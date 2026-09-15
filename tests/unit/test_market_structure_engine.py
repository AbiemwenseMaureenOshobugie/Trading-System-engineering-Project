"""Tests for the deterministic MS-0.1A H1 market-structure engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.domain import MarketCandle, PriceZone, Regime, SwingKind, Timeframe
from trading_system.strategy.market_structure import H1MarketStructureEngine
from trading_system.strategy.market_structure.engine import _Candidate, _Confirmed

UTC = timezone.utc


def candle(i: int, open_: str, high: str, low: str, close: str) -> MarketCandle:
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=start,
        timestamp_close=start + timedelta(hours=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def confirmed(i: int, kind: SwingKind, price: str) -> _Confirmed:
    if kind is SwingKind.HIGH:
        c = candle(i, price, price, "1.0000", price)
    else:
        c = candle(i, price, "1.1000", price, price)
    return _Confirmed(_Candidate(i, kind, c), c.timestamp_close)


def test_empty_history_is_initial_unclear() -> None:
    state = H1MarketStructureEngine().evaluate(
        candles=[],
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert state.regime is Regime.UNCLEAR
    assert "INITIAL_UNCLEAR_INSUFFICIENT_HISTORY" in state.structural_events


def test_dual_candidate_is_rejected() -> None:
    candles = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0900", "1.1000"),
        candle(2, "1.1000", "1.1050", "1.0950", "1.1000"),
    ]
    state = H1MarketStructureEngine().evaluate(
        candles=candles,
        evaluation_cutoff=candles[-1].timestamp_close,
    )
    assert state.meaningful_highs == ()
    assert state.meaningful_lows == ()
    assert any(event.startswith("DUAL_CANDIDATE_REJECTED:") for event in state.structural_events)


def test_cutoff_excludes_later_candles() -> None:
    early = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0980", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    ]
    later = early + [
        candle(3, "1.1020", "1.1200", "1.1000", "1.1180"),
        candle(4, "1.1180", "1.1190", "1.0900", "1.0920"),
    ]
    engine = H1MarketStructureEngine()
    cutoff = early[-1].timestamp_close
    assert engine.evaluate(candles=later, evaluation_cutoff=cutoff) == engine.evaluate(
        candles=early, evaluation_cutoff=cutoff
    )


def test_t19_bounding_pair_uses_actual_price_bounds_not_chronology() -> None:
    highs = [
        confirmed(1, SwingKind.HIGH, "1.1200"),
        confirmed(5, SwingKind.HIGH, "1.1100"),
        confirmed(9, SwingKind.HIGH, "1.1300"),
    ]
    lows = [
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(10, SwingKind.LOW, "1.0950"),
    ]
    upper, lower = H1MarketStructureEngine._bounding_pair(highs, lows)
    assert upper == PriceZone(Decimal("1.1300"), Decimal("1.1300"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0800"))


def test_t20_state_exposes_explicit_boundary_fields() -> None:
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    lower = PriceZone(Decimal("1.0800"), Decimal("1.0850"))
    state = H1MarketStructureEngine._state(
        Regime.RANGE, (), (), None, upper, lower, (), datetime(2026, 1, 2, tzinfo=UTC)
    )
    assert state.range_upper_boundary == upper
    assert state.range_lower_boundary == lower


def test_t21_boundary_values_are_not_mutated_by_reaction_evaluation() -> None:
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    lower = PriceZone(Decimal("1.0800"), Decimal("1.0850"))
    meaningful = [
        confirmed(1, SwingKind.HIGH, "1.1230"),
        confirmed(2, SwingKind.LOW, "1.0830"),
        confirmed(3, SwingKind.HIGH, "1.1240"),
    ]
    H1MarketStructureEngine()._range_reactions(meaningful, upper, lower)
    assert upper == PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0850"))


def test_t22_alternating_reactions_can_start_from_either_side() -> None:
    t = datetime(2026, 1, 1, tzinfo=UTC)
    assert H1MarketStructureEngine._alternates(
        [t, t + timedelta(hours=2)],
        [t + timedelta(hours=1), t + timedelta(hours=3)],
    )
    assert H1MarketStructureEngine._alternates(
        [t + timedelta(hours=1), t + timedelta(hours=3)],
        [t, t + timedelta(hours=2)],
    )


def test_t23_earlier_non_bounding_swing_is_not_selected() -> None:
    highs = [
        confirmed(1, SwingKind.HIGH, "1.1150"),
        confirmed(4, SwingKind.HIGH, "1.1200"),
        confirmed(7, SwingKind.HIGH, "1.1180"),
    ]
    lows = [
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(5, SwingKind.LOW, "1.0800"),
        confirmed(8, SwingKind.LOW, "1.0850"),
    ]
    upper, lower = H1MarketStructureEngine._bounding_pair(highs, lows)
    assert upper == PriceZone(Decimal("1.1200"), Decimal("1.1200"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0800"))


def test_t24_later_candidates_cannot_change_an_earlier_cutoff_state() -> None:
    base = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0980", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    ]
    extended = base + [
        candle(3, "1.1020", "1.1300", "1.1000", "1.1250"),
        candle(4, "1.1250", "1.1260", "1.0750", "1.0800"),
    ]
    cutoff = base[-1].timestamp_close
    engine = H1MarketStructureEngine()
    assert engine.evaluate(candles=extended, evaluation_cutoff=cutoff) == engine.evaluate(
        candles=base, evaluation_cutoff=cutoff
    )
