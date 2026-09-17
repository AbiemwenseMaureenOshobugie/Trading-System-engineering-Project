"""Tests for the deterministic MS-0.3 confirmation engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.domain import (
    ConfirmationType,
    Direction,
    KeyLevel,
    KeyLevelSource,
    MarketCandle,
    MarketStructureState,
    PriceZone,
    Regime,
    SwingKind,
    SwingPoint,
    Timeframe,
)
from trading_system.strategy.confirmation import M15ConfirmationEngine, M15SwingDetector

UTC = timezone.utc
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def m15(i: int, open_: str, high: str, low: str, close: str) -> MarketCandle:
    start = BASE + timedelta(minutes=15 * i)
    return MarketCandle(
        symbol="EURUSD", timeframe=Timeframe.M15,
        timestamp_open=start, timestamp_close=start + timedelta(minutes=15),
        open=Decimal(open_), high=Decimal(high), low=Decimal(low), close=Decimal(close),
    )


def key_level() -> KeyLevel:
    return KeyLevel(
        key_level_id="KL-TEST",
        source_types=(KeyLevelSource.VALIDATED_SWING,),
        source_zones=((KeyLevelSource.VALIDATED_SWING, PriceZone(Decimal("1.1000"), Decimal("1.1050"))),),
        active=True, role=None, created_at=BASE, updated_at=BASE,
        evidence_refs=("test",), state_history=("ACTIVE",),
    )


def uptrend() -> MarketStructureState:
    control = SwingPoint(BASE, Decimal("1.0950"), SwingKind.LOW)
    return MarketStructureState(
        regime=Regime.UPTREND, structure_version="MS-0.1A",
        meaningful_highs=(), meaningful_lows=(control,), controlling_level=control,
        range_upper_boundary=None, range_lower_boundary=None,
        structural_events=(), evaluated_at=BASE,
    )


def downtrend() -> MarketStructureState:
    control = SwingPoint(BASE, Decimal("1.1050"), SwingKind.HIGH)
    return MarketStructureState(
        regime=Regime.DOWNTREND, structure_version="MS-0.1A",
        meaningful_highs=(control,), meaningful_lows=(), controlling_level=control,
        range_upper_boundary=None, range_lower_boundary=None,
        structural_events=(), evaluated_at=BASE,
    )


def test_m15_detector_implements_corrected_three_condition_high_and_low() -> None:
    candles = (
        m15(0, "1.1000", "1.1050", "1.0980", "1.1030"),
        m15(1, "1.1030", "1.1100", "1.1010", "1.1080"),
        m15(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    )
    swings = M15SwingDetector().confirm(candles=candles)
    assert len(swings) == 1
    assert swings[0].swing.kind is SwingKind.HIGH
    assert swings[0].confirmed_at == candles[2].timestamp_close


def test_cp2_ordinary_buy_triggers_on_c3() -> None:
    candles = (
        m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),
        m15(1, "1.1040", "1.1080", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1100", "1.1060", "1.1090"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    cp2 = [x for x in results if x.confirmation_type is ConfirmationType.CP2]
    assert cp2
    assert cp2[0].state == "TRIGGERED"
    assert cp2[0].signal_status == "SIGNAL_TRIGGERED"


def test_cp2_ordinary_buy_expires_when_c3_fails() -> None:
    candles = (
        m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),
        m15(1, "1.1040", "1.1080", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1080", "1.1060", "1.1075"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    cp2 = [x for x in results if x.confirmation_type is ConfirmationType.CP2]
    assert cp2[0].state == "EXPIRED"


def test_cp2_sweep_buy_freezes_c1_low_and_triggers() -> None:
    candles = (
        m15(0, "1.1020", "1.1050", "1.0970", "1.1040"),
        m15(1, "1.1040", "1.1090", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1110", "1.1060", "1.1100"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    cp2 = [x for x in results if x.confirmation_type is ConfirmationType.CP2]
    assert cp2[0].state == "TRIGGERED"
    assert cp2[0].controlling_extreme == Decimal("1.0970")


def test_cp2_sweep_buy_repenetration_invalidates_sequence() -> None:
    candles = (
        m15(0, "1.1020", "1.1050", "1.0970", "1.1040"),
        m15(1, "1.1040", "1.1090", "1.0965", "1.1070"),
        m15(2, "1.1070", "1.1110", "1.1060", "1.1100"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    cp2 = [x for x in results if x.confirmation_type is ConfirmationType.CP2]
    assert cp2[0].state == "INVALIDATED"
    assert cp2[0].invalidation_reason == "SWEEP_REPENETRATION"


def test_cp2_respects_h1_directional_gate() -> None:
    candles = (
        m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),
        m15(1, "1.1040", "1.1080", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1100", "1.1060", "1.1090"),
    )
    range_state = MarketStructureState(
        regime=Regime.RANGE, structure_version="MS-0.1A", meaningful_highs=(), meaningful_lows=(),
        controlling_level=None, range_upper_boundary=None, range_lower_boundary=None,
        structural_events=(), evaluated_at=BASE,
    )
    assert M15ConfirmationEngine().evaluate(candles=candles, structure=range_state, setup_key_level=key_level()) == ()


def test_inactive_governing_key_level_blocks_confirmation() -> None:
    level = key_level()
    inactive = KeyLevel(
        key_level_id=level.key_level_id, source_types=level.source_types, source_zones=level.source_zones,
        active=False, role=level.role, created_at=level.created_at, updated_at=level.updated_at,
        evidence_refs=level.evidence_refs, state_history=level.state_history,
    )
    candles = (m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),)
    assert M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=inactive) == ()


def test_setup_key_level_is_preserved_on_output() -> None:
    candles = (
        m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),
        m15(1, "1.1040", "1.1080", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1100", "1.1060", "1.1090"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    assert results
    assert all(result.setup_key_level == "KL-TEST" for result in results)


def test_cp2_sell_uses_directional_rules() -> None:
    candles = (
        m15(0, "1.1020", "1.1070", "1.1010", "1.1010"),
        m15(1, "1.1010", "1.1010", "1.0960", "1.0970"),
        m15(2, "1.0970", "1.0980", "1.0920", "1.0930"),
    )
    results = M15ConfirmationEngine().evaluate(candles=candles, structure=downtrend(), setup_key_level=key_level())
    cp2 = [x for x in results if x.confirmation_type is ConfirmationType.CP2]
    assert cp2
    assert cp2[0].state == "TRIGGERED"


def test_confirmation_ids_are_deterministic() -> None:
    candles = (
        m15(0, "1.1030", "1.1040", "1.0980", "1.1040"),
        m15(1, "1.1040", "1.1080", "1.1040", "1.1070"),
        m15(2, "1.1070", "1.1100", "1.1060", "1.1090"),
    )
    engine = M15ConfirmationEngine()
    first = engine.evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    second = engine.evaluate(candles=candles, structure=uptrend(), setup_key_level=key_level())
    assert first == second
