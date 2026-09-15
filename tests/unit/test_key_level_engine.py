"""Tests for the deterministic MS-0.2 Key-Level detection engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.domain import (
    KeyLevelSource, MarketCandle, MarketStructureState, PriceZone,
    Regime, SwingKind, SwingPoint, Timeframe,
)
from trading_system.strategy.key_levels import KeyLevelDetectionEngine

UTC = timezone.utc
EVALUATED_AT = datetime(2026, 1, 10, tzinfo=UTC)


def candle(i: int, open_: str, high: str, low: str, close: str) -> MarketCandle:
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
    return MarketCandle(
        symbol="EURUSD", timeframe=Timeframe.H1,
        timestamp_open=start, timestamp_close=start + timedelta(hours=1),
        open=Decimal(open_), high=Decimal(high), low=Decimal(low), close=Decimal(close),
    )


def state(*, highs=(), lows=(), upper=None, lower=None, events=()):
    return MarketStructureState(
        regime=Regime.RANGE, structure_version="MS-0.1A",
        meaningful_highs=highs, meaningful_lows=lows, controlling_level=None,
        range_upper_boundary=upper, range_lower_boundary=lower,
        structural_events=events, evaluated_at=EVALUATED_AT,
    )


def test_klt01_validated_swing_uses_immutable_ms01a_zone():
    c = candle(2, "1.1040", "1.1100", "1.1000", "1.1060")
    swing = SwingPoint(c.timestamp_open, Decimal("1.1100"), SwingKind.HIGH)
    levels = KeyLevelDetectionEngine().detect(candles=(c,), structure=state(highs=(swing,)))
    assert levels[0].source_zones == ((KeyLevelSource.VALIDATED_SWING, PriceZone(Decimal("1.1100"), Decimal("1.1060"))),)


def test_klt02_range_boundaries_are_consumed_without_reconstruction():
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    lower = PriceZone(Decimal("1.0800"), Decimal("1.0850"))
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=upper, lower=lower))
    assert {level.source_zones for level in levels} == {
        ((KeyLevelSource.RANGE_BOUNDARY, upper),), ((KeyLevelSource.RANGE_BOUNDARY, lower),)
    }


def test_klt03_range_breakout_keeps_boundary_geometry():
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=upper, events=("RANGE_BREAKOUT_UP",)))
    assert len(levels) == 1
    assert set(levels[0].source_types) == {KeyLevelSource.RANGE_BOUNDARY, KeyLevelSource.BREAKOUT_LEVEL}
    assert all(zone == upper for _, zone in levels[0].source_zones)


def test_klt04_role_reversal_preserves_existing_source_zone():
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=upper, events=("ROLE_REVERSAL:RANGE_BOUNDARY:UPPER",)))
    assert len(levels) == 1
    assert KeyLevelSource.ROLE_REVERSAL in levels[0].source_types
    assert (KeyLevelSource.ROLE_REVERSAL, upper) in levels[0].source_zones


def test_klt05_only_established_sources_are_detected():
    assert KeyLevelDetectionEngine().detect(candles=(), structure=state()) == ()


def test_klt06_overlapping_sources_consolidate_and_preserve_all_geometry():
    c = candle(2, "1.1040", "1.1100", "1.1000", "1.1060")
    swing = SwingPoint(c.timestamp_open, Decimal("1.1100"), SwingKind.HIGH)
    boundary = PriceZone(Decimal("1.1050"), Decimal("1.1120"))
    levels = KeyLevelDetectionEngine().detect(candles=(c,), structure=state(highs=(swing,), upper=boundary))
    assert len(levels) == 1
    assert set(levels[0].source_types) == {KeyLevelSource.VALIDATED_SWING, KeyLevelSource.RANGE_BOUNDARY}
    assert len(levels[0].source_zones) == 2


def test_klt07_non_overlapping_sources_remain_separate():
    candles = (candle(2, "1.1040", "1.1100", "1.1000", "1.1060"), candle(8, "1.0940", "1.1000", "1.0900", "1.0960"))
    highs = (SwingPoint(candles[0].timestamp_open, Decimal("1.1100"), SwingKind.HIGH), SwingPoint(candles[1].timestamp_open, Decimal("1.1000"), SwingKind.HIGH))
    assert len(KeyLevelDetectionEngine().detect(candles=candles, structure=state(highs=highs))) == 2


def test_klt08_consolidation_does_not_mutate_source_zones():
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=upper, events=("RANGE_BREAKOUT_UP",)))
    assert upper == PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    assert all(zone == upper for _, zone in levels[0].source_zones)


def test_klt09_multiple_provenance_is_retained():
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    events = ("RANGE_BREAKOUT_UP", "ROLE_REVERSAL:RANGE_BOUNDARY:UPPER")
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=upper, events=events))
    assert set(levels[0].source_types) == {KeyLevelSource.RANGE_BOUNDARY, KeyLevelSource.BREAKOUT_LEVEL, KeyLevelSource.ROLE_REVERSAL}
    assert len(levels[0].evidence_refs) == 3


def test_klt10_engine_does_not_select_governing_setup_key_level():
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250")), lower=PriceZone(Decimal("1.0800"), Decimal("1.0850"))))
    assert len(levels) == 2
    assert all(level.active for level in levels)


def test_klt11_no_independent_expiry_is_applied():
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250"))))
    assert levels[0].active is True


def test_klt12_source_state_history_is_retained():
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250"))))
    assert "SOURCE_ESTABLISHED:RANGE_BOUNDARY" in levels[0].state_history


def test_klt13_no_numerical_merge_tolerance_is_used():
    first = PriceZone(Decimal("1.1000"), Decimal("1.1010"))
    second = PriceZone(Decimal("1.1011"), Decimal("1.1020"))
    assert len(KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=first, lower=second))) == 2


def test_klt14_identical_inputs_produce_identical_identity_and_provenance():
    structure = state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250")), events=("RANGE_BREAKOUT_UP",))
    engine = KeyLevelDetectionEngine()
    assert engine.detect(candles=(), structure=structure) == engine.detect(candles=(), structure=structure)


def test_klt15_ms01a_structure_is_consumed_without_regime_change():
    structure = state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250")))
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=structure)
    assert structure.regime is Regime.RANGE
    assert levels[0].source_types == (KeyLevelSource.RANGE_BOUNDARY,)


def test_klt16_cp2_is_not_implemented_by_key_level_engine():
    levels = KeyLevelDetectionEngine().detect(candles=(), structure=state(upper=PriceZone(Decimal("1.1200"), Decimal("1.1250"))))
    assert not any("CP-2" in event for level in levels for event in level.state_history)
