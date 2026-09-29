"""Tests for deterministic MS-0.22 setup classification."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import ConfirmationSequence, ConfirmationType, Direction
from trading_system.strategy.classification import SetupClassifier

TS = datetime(2026, 1, 1, 11, 0, tzinfo=timezone.utc)


def triggered(
    *,
    confirmation_type: ConfirmationType = ConfirmationType.CP1,
    setup_id: str = "CN-001",
) -> ConfirmationSequence:
    return ConfirmationSequence(
        setup_id=setup_id,
        confirmation_type=confirmation_type,
        direction=Direction.BUY,
        setup_key_level="KL-001",
        state="TRIGGERED",
        candle_refs=("candle:1", "candle:2", "candle:3"),
        controlling_extreme=Decimal("1.0950"),
        signal_status="SIGNAL_TRIGGERED",
        invalidation_reason=None,
        symbol="EURUSD",
        signal_timestamp=TS,
        signal_entry_price=Decimal("1.1050"),
    )


def test_triggered_confirmation_becomes_candidate() -> None:
    candidate = SetupClassifier().classify((triggered(),))[0]
    assert candidate.symbol == "EURUSD"
    assert candidate.direction is Direction.BUY
    assert candidate.setup_type is ConfirmationType.CP1
    assert candidate.setup_id == "CN-001"
    assert candidate.signal_timestamp == TS
    assert candidate.signal_entry_price == Decimal("1.1050")
    assert candidate.proposed_stop_loss is None
    assert candidate.proposed_target is None


def test_non_triggered_confirmation_produces_no_candidate() -> None:
    confirmation = triggered()
    pending = ConfirmationSequence(
        setup_id=confirmation.setup_id,
        confirmation_type=confirmation.confirmation_type,
        direction=confirmation.direction,
        setup_key_level=confirmation.setup_key_level,
        state="PENDING_TRIGGER",
        candle_refs=confirmation.candle_refs,
        controlling_extreme=confirmation.controlling_extreme,
        signal_status="PENDING",
        invalidation_reason=None,
        symbol=confirmation.symbol,
    )
    assert SetupClassifier().classify((pending,)) == ()


def test_cp2_trigger_is_classified_without_reinterpreting_entry() -> None:
    candidate = SetupClassifier().classify(
        (triggered(confirmation_type=ConfirmationType.CP2, setup_id="CN-002"),)
    )[0]
    assert candidate.setup_type is ConfirmationType.CP2
    assert candidate.signal_entry_price == Decimal("1.1050")
    assert candidate.signal_timestamp == TS


def test_decision_id_is_deterministic() -> None:
    classifier = SetupClassifier()
    first = classifier.classify((triggered(),))[0]
    second = classifier.classify((triggered(),))[0]
    assert first.decision_id == second.decision_id
    assert first.decision_id.startswith("DEC-")
    assert len(first.decision_id) == 68


def test_symbol_and_evidence_are_preserved() -> None:
    candidate = SetupClassifier().classify((triggered(),))[0]
    assert candidate.symbol == "EURUSD"
    assert candidate.evidence_refs == (
        "confirmation:CN-001",
        "key_level:KL-001",
        "candle:candle:1",
        "candle:candle:2",
        "candle:candle:3",
        "confirmation_type:CP-1",
    )


def test_triggered_confirmation_requires_trigger_fields() -> None:
    confirmation = triggered()
    missing_timestamp = ConfirmationSequence(
        setup_id=confirmation.setup_id,
        confirmation_type=confirmation.confirmation_type,
        direction=confirmation.direction,
        setup_key_level=confirmation.setup_key_level,
        state="TRIGGERED",
        candle_refs=confirmation.candle_refs,
        controlling_extreme=confirmation.controlling_extreme,
        signal_status="SIGNAL_TRIGGERED",
        invalidation_reason=None,
        symbol="EURUSD",
        signal_timestamp=None,
        signal_entry_price=confirmation.signal_entry_price,
    )
    try:
        SetupClassifier().classify((missing_timestamp,))
    except ValueError as exc:
        assert str(exc) == "triggered confirmation requires signal_timestamp"
    else:
        raise AssertionError("expected ValueError")
