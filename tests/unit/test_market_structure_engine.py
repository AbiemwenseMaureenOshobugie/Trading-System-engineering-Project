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


def test_candidate_zones_use_ordered_body_to_extreme_boundaries() -> None:
    high_candle = candle(20, "1.1000", "1.1100", "1.0950", "1.1050")
    low_candle = candle(21, "1.1000", "1.1050", "1.0900", "1.0950")
    high = _Candidate(20, SwingKind.HIGH, high_candle)
    low = _Candidate(21, SwingKind.LOW, low_candle)
    assert high.zone == PriceZone(Decimal("1.1050"), Decimal("1.1100"))
    assert low.zone == PriceZone(Decimal("1.0900"), Decimal("1.0950"))


def test_r56_replacement_downtrend_established_after_uptrend_invalidation_is_not_transition() -> None:
    # MS-0.1A §8: "`TRANSITION` exists only after an established regime is invalidated/structurally
    # changed and a replacement regime is not yet established."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW, "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(7, SwingKind.HIGH, "1.1100"),
        confirmed(8, SwingKind.LOW, "1.0900"),  # old controlling HL
        confirmed(10, SwingKind.HIGH, "1.1000"),  # LH
        confirmed(11, SwingKind.LOW, "1.0850"),  # LL
        confirmed(12, SwingKind.HIGH, "1.0950"),  # LH, controlling LH
        confirmed(13, SwingKind.LOW, "1.0800"),  # LL
    ]
    labels = engine._relationship_labels(swings)
    assert list(labels.values()).count("LH") >= 2  # precondition: replacement DOWNTREND evidence
    assert list(labels.values()).count("LL") >= 2
    # Completed close 1.0850 below old controlling HL 1.0900 (before the LH/LL swings),
    # and no close above controlling LH 1.0950 afterwards.
    invalidation = [candle(9, "1.0900", "1.0910", "1.0840", "1.0850")]
    regime, controlling, _, _ = engine._classify(invalidation, swings, labels, [])
    assert regime is Regime.DOWNTREND, (
        f"old UPTREND invalidated by close 1.0850 < HL 1.0900; replacement DOWNTREND "
        f"(LH 1.1000/1.0950, LL 1.0850/1.0800, controlling LH 1.0950) is established, "
        f"so TRANSITION must not be reported; regime was {regime}"
    )
    assert controlling == swings[10].swing


def test_r57_invalidated_structure_is_non_controlling_in_transition() -> None:
    # MS-0.1A §8: "Invalidated structure remains historical but becomes inactive and non-controlling."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW, "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(7, SwingKind.HIGH, "1.1100"),
        confirmed(8, SwingKind.LOW, "1.0900"),  # controlling HL, about to be invalidated
    ]
    labels = engine._relationship_labels(swings)
    invalidation = [candle(9, "1.0900", "1.0910", "1.0840", "1.0850")]
    regime, controlling, _, _ = engine._classify(invalidation, swings, labels, [])
    assert regime is Regime.TRANSITION  # precondition: no replacement swings exist yet
    assert controlling != swings[-1].swing, (
        f"HL {swings[-1].swing.price} was invalidated by close 1.0850 and must be "
        f"non-controlling, but controlling_level is still {controlling}"
    )


def test_r59_no_range_breakout_recorded_while_trend_is_established() -> None:
    # MS-0.1A §9 condition 5: "no sustained directional progression sufficient for UPTREND or DOWNTREND."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW, "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(7, SwingKind.HIGH, "1.1100"),
        confirmed(8, SwingKind.LOW, "1.0900"),
    ]
    labels = engine._relationship_labels(swings)
    assert list(labels.values()).count("HH") >= 2  # precondition: trend sufficient
    assert list(labels.values()).count("HL") >= 2
    events: list[str] = []
    later = [candle(20, "1.1100", "1.1160", "1.1090", "1.1150")]
    regime, _, _, _ = engine._classify(later, swings, labels, events)
    breakouts = [e for e in events if e.startswith("RANGE_BREAKOUT")]
    assert not breakouts, (
        f"HH 1.0900/1.1000/1.1100 and HL 1.0700/1.0800/1.0900 are sufficient for UPTREND, "
        f"so no valid range exists and no range breakout may be recorded; got {breakouts}"
    )
    assert regime is not Regime.RANGE


def test_r65_range_penetration_is_decided_by_next_completed_candle() -> None:
    # MS-0.1A §9: a penetration is a completed close "on or past the outer edge of the boundary zone,
    # inclusive"; "The immediately following H1 candle determines whether that penetration failed or
    # was confirmed"; no following candle -> "provisional"; a following close beyond the opposite
    # boundary fails the original penetration and starts a separate opposite-direction evaluation;
    # "'Immediately following' means the next completed candle in the evaluated sequence; gaps in
    # market time do not affect the rule."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.1100"),
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(3, SwingKind.HIGH, "1.1100"),
        confirmed(4, SwingKind.LOW, "1.0900"),
    ]  # upper boundary 1.1100, lower boundary 1.0900, alternating, no trend
    labels = engine._relationship_labels(swings)

    def at(i: int, close: str) -> MarketCandle:
        value = Decimal(close)
        return candle(i, close, str(value + Decimal("0.0005")), str(value - Decimal("0.0005")), close)

    cases = [
        ("confirmed: 1.1150 then 1.1180 (precondition)", [at(6, "1.1150"), at(7, "1.1180")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
        ("failed: 1.1150 then inside 1.1050", [at(6, "1.1150"), at(7, "1.1050")], Regime.RANGE, None),
        ("inclusive upper edge: 1.1100 then 1.1100", [at(6, "1.1100"), at(7, "1.1100")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
        ("inclusive lower edge: 1.0900 then 1.0900", [at(6, "1.0900"), at(7, "1.0900")], Regime.TRANSITION, "RANGE_BREAKOUT_DOWN"),
        ("provisional: 1.1150 with no following candle", [at(6, "1.1150")], Regime.RANGE, None),
        ("opposite: 1.1150 then beyond lower 1.0850 (opposite provisional)", [at(6, "1.1150"), at(7, "1.0850")], Regime.RANGE, None),
        ("opposite confirmed separately: 1.1150, 1.0850, 1.0800", [at(6, "1.1150"), at(7, "1.0850"), at(8, "1.0800")], Regime.TRANSITION, "RANGE_BREAKOUT_DOWN"),
        ("gap, inside: 1.1150 then 1.1050 twenty-four hours later", [at(6, "1.1150"), at(30, "1.1050")], Regime.RANGE, None),
        ("gap, beyond: 1.1150 then 1.1180 twenty-four hours later (precondition)", [at(6, "1.1150"), at(30, "1.1180")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
    ]
    divergences = []
    for name, candles, expected_regime, expected_event in cases:
        events: list[str] = []
        regime, _, _, _ = engine._classify(candles, swings, labels, events)
        breakouts = [e for e in events if e.startswith("RANGE_BREAKOUT")]
        expected_events = [expected_event] if expected_event else []
        if regime is not expected_regime or breakouts != expected_events:
            divergences.append(
                f"{name}: expected {expected_regime.name} {expected_events}, "
                f"got {regime.name} {breakouts}"
            )
    assert not divergences, (
        f"{len(divergences)} of {len(cases)} MS-0.1A §9 penetration cases diverge "
        f"(upper 1.1100 / lower 1.0900): " + " | ".join(divergences)
    )


def test_r68_established_uptrend_persists_after_close_above_last_swing_high() -> None:
    # MS-0.1A §10: "An established regime persists while its defining conditions remain valid."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),  # HH
        confirmed(4, SwingKind.LOW, "1.0700"),  # HL
        confirmed(5, SwingKind.HIGH, "1.1000"),  # HH
        confirmed(6, SwingKind.LOW, "1.0800"),  # HL
        confirmed(7, SwingKind.HIGH, "1.1100"),  # HH
        confirmed(8, SwingKind.LOW, "1.0900"),  # HL, controlling
    ]
    labels = engine._relationship_labels(swings)
    before, _, _, _ = engine._classify([], swings, labels, [])
    assert before is Regime.UPTREND  # precondition: 3 HH, 3 HL, controlling HL intact

    # One later close above the last swing high; no close below controlling HL 1.0900.
    later = [candle(20, "1.1100", "1.1160", "1.1090", "1.1150")]
    regime, controlling, _, _ = engine._classify(later, swings, labels, [])
    assert regime is Regime.UPTREND, (
        f"UPTREND (HH 1.0900/1.1000/1.1100, HL 1.0700/1.0800/1.0900, controlling HL "
        f"{swings[-1].swing.price}) must persist; a close of 1.1150 above last HH 1.1100 "
        f"does not break the controlling HL, but regime was {regime}"
    )
    assert controlling == swings[-1].swing
