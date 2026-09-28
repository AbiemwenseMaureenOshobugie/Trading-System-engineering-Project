"""Tests for canonical GKS governing Key-Level selection."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import (
    Direction,
    GoverningKeyLevelRequest,
    GoverningKeyLevelStatus,
    KeyLevel,
    KeyLevelSource,
    MarketStructureState,
    PriceZone,
    Regime,
    SwingKind,
    SwingPoint,
)
from trading_system.strategy.governing_key_level import GoverningKeyLevelEngine

TS = datetime(2026, 1, 15, 8, 0, tzinfo=timezone.utc)
ZONE = PriceZone(Decimal("1.0950"), Decimal("1.1000"))


def structure(direction_kind=SwingKind.LOW):
    controlling = SwingPoint(TS, Decimal("1.0950"), direction_kind)
    return MarketStructureState(
        regime=Regime.UPTREND if direction_kind is SwingKind.LOW else Regime.DOWNTREND,
        structure_version="MS-0.1A",
        meaningful_highs=(),
        meaningful_lows=(),
        controlling_level=controlling,
        range_upper_boundary=None,
        range_lower_boundary=None,
        structural_events=(),
        evaluated_at=TS,
    )


def level(
    *,
    key_level_id="KL-1",
    role="SUPPORT",
    active=True,
    evidence_ref="SWING:LOW:2026-01-15T08:00:00+00:00",
):
    return KeyLevel(
        key_level_id=key_level_id,
        source_types=(KeyLevelSource.VALIDATED_SWING,),
        source_zones=((KeyLevelSource.VALIDATED_SWING, ZONE),),
        active=active,
        role=role,
        created_at=TS,
        updated_at=TS,
        evidence_refs=(evidence_ref,),
        state_history=("SOURCE_ESTABLISHED:MEANINGFUL_SWING",),
    )


def request(*levels, direction=Direction.BUY):
    return GoverningKeyLevelRequest(
        structure=structure(SwingKind.LOW if direction is Direction.BUY else SwingKind.HIGH),
        direction=direction,
        key_levels=levels,
    )


def test_selects_exactly_one_associated_compatible_active_key_level():
    result = GoverningKeyLevelEngine().select(request(level()))
    assert result.status is GoverningKeyLevelStatus.SELECTED
    assert result.selected_key_level == level()
    assert result.controlling_level_evidence_ref == "SWING:LOW:2026-01-15T08:00:00+00:00"


def test_buy_requires_support_role():
    result = GoverningKeyLevelEngine().select(request(level(role="RESISTANCE")))
    assert result.status is GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL


def test_sell_requires_resistance_role():
    result = GoverningKeyLevelEngine().select(
        request(
            level(
                role="RESISTANCE",
                evidence_ref="SWING:HIGH:2026-01-15T08:00:00+00:00",
            ),
            direction=Direction.SELL,
        )
    )
    assert result.status is GoverningKeyLevelStatus.SELECTED


def test_inactive_level_is_ineligible():
    result = GoverningKeyLevelEngine().select(request(level(active=False)))
    assert result.status is GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL


def test_exact_evidence_reference_is_required():
    result = GoverningKeyLevelEngine().select(
        request(level(evidence_ref="SWING:LOW:2026-01-15T08:00:00+00"))
    )
    assert result.status is GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL


def test_missing_controlling_level_produces_no_governing_level():
    state = structure()
    state = MarketStructureState(
        regime=state.regime,
        structure_version=state.structure_version,
        meaningful_highs=state.meaningful_highs,
        meaningful_lows=state.meaningful_lows,
        controlling_level=None,
        range_upper_boundary=state.range_upper_boundary,
        range_lower_boundary=state.range_lower_boundary,
        structural_events=state.structural_events,
        evaluated_at=state.evaluated_at,
    )
    result = GoverningKeyLevelEngine().select(
        GoverningKeyLevelRequest(state, Direction.BUY, (level(),))
    )
    assert result.status is GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL
    assert result.controlling_level_evidence_ref is None


def test_multiple_matching_levels_are_structural_consistency_failure():
    result = GoverningKeyLevelEngine().select(request(level(), level(key_level_id="KL-2")))
    assert result.status is GoverningKeyLevelStatus.STRUCTURAL_CONSISTENCY_FAILURE
    assert result.selected_key_level is None
    assert result.eligible_key_level_ids == ("KL-1", "KL-2")


def test_mixed_source_key_level_uses_evidence_reference_for_association():
    mixed = KeyLevel(
        key_level_id="KL-MIXED",
        source_types=(KeyLevelSource.VALIDATED_SWING, KeyLevelSource.RANGE_BOUNDARY),
        source_zones=(
            (KeyLevelSource.VALIDATED_SWING, ZONE),
            (KeyLevelSource.RANGE_BOUNDARY, ZONE),
        ),
        active=True,
        role="SUPPORT",
        created_at=TS,
        updated_at=TS,
        evidence_refs=(
            "RANGE_BOUNDARY:LOWER",
            "SWING:LOW:2026-01-15T08:00:00+00:00",
        ),
        state_history=("SOURCE_ESTABLISHED:MEANINGFUL_SWING",),
    )
    result = GoverningKeyLevelEngine().select(request(mixed))
    assert result.status is GoverningKeyLevelStatus.SELECTED
    assert result.selected_key_level == mixed


def test_role_or_source_type_does_not_establish_structural_association():
    unrelated = level(
        key_level_id="KL-2",
        evidence_ref="SWING:LOW:2026-01-16T08:00:00+00:00",
    )
    result = GoverningKeyLevelEngine().select(request(unrelated))
    assert result.status is GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL
