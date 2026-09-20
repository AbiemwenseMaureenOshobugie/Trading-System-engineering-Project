"""Tests for the deterministic MS-0.7 paper execution contract."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    DecisionResult,
    DecisionStatus,
    Direction,
    ExecutionState,
    GovernanceResult,
    GovernanceStatus,
    RiskResult,
    RiskStatus,
)
from trading_system.execution import (
    ExecutionEngine,
    ExecutionStateMachine,
    InvalidExecutionTransition,
)

TS = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


class AuditSink:
    def __init__(self) -> None:
        self.events = []

    def record(self, event) -> None:
        self.events.append(event)


def candidate() -> DecisionCandidate:
    return DecisionCandidate(
        decision_id="D-001",
        strategy_version="MS-0.6",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id="SETUP-001",
        signal_timestamp=TS,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0949"),
        proposed_target=Decimal("1.1102"),
        evidence_refs=("E-001",),
    )


def risk() -> RiskResult:
    return RiskResult(
        decision_id="D-001",
        requested_risk=Decimal("0.01"),
        approved_risk=Decimal("0.01"),
        position_size=Decimal("1000"),
        entry_assumption=Decimal("1.1000"),
        structural_stop_loss=Decimal("1.0950"),
        final_stop_loss=Decimal("1.0949"),
        target_price=Decimal("1.1102"),
        stop_distance=Decimal("0.0051"),
        target_distance=Decimal("0.0102"),
        risk_reward=Decimal("2"),
        risk_amount=Decimal("100"),
        status=RiskStatus.RISK_AUTHORIZED,
        reason_codes=("RISK_AUTHORIZED",),
    )


def governance() -> GovernanceResult:
    return GovernanceResult(
        decision_id="D-001",
        instrument_session_eligible=True,
        daily_trade_count=0,
        daily_loss_count=0,
        checks=("SESSION_ELIGIBLE",),
        status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        reason_codes=("GOVERNANCE_AUTHORIZED",),
    )


def decision() -> DecisionResult:
    return DecisionResult(
        decision_id="D-001",
        status=DecisionStatus.VALID,
        reason_codes=("RISK_AUTHORIZED", "GOVERNANCE_AUTHORIZED"),
    )


def test_execution_requires_all_three_authorizations():
    sink = AuditSink()
    engine = ExecutionEngine(audit_port=sink, clock=lambda: TS)
    bad = DecisionResult("D-001", DecisionStatus.WAIT, ("RISK_PENDING",))

    with pytest.raises(PermissionError):
        engine.submit(
            candidate=candidate(),
            decision=bad,
            risk=risk(),
            governance=governance(),
        )


def test_execution_requires_matching_decision_ids():
    sink = AuditSink()
    engine = ExecutionEngine(audit_port=sink, clock=lambda: TS)
    bad_risk = RiskResult(
        decision_id="D-999",
        requested_risk=risk().requested_risk,
        approved_risk=risk().approved_risk,
        position_size=risk().position_size,
        entry_assumption=risk().entry_assumption,
        structural_stop_loss=risk().structural_stop_loss,
        final_stop_loss=risk().final_stop_loss,
        target_price=risk().target_price,
        stop_distance=risk().stop_distance,
        target_distance=risk().target_distance,
        risk_reward=risk().risk_reward,
        risk_amount=risk().risk_amount,
        status=risk().status,
        reason_codes=risk().reason_codes,
    )

    with pytest.raises(PermissionError):
        engine.submit(
            candidate=candidate(),
            decision=decision(),
            risk=bad_risk,
            governance=governance(),
        )


def test_paper_execution_is_immediately_filled_at_requested_price():
    sink = AuditSink()
    engine = ExecutionEngine(audit_port=sink, clock=lambda: TS)

    record = engine.submit(
        candidate=candidate(),
        decision=decision(),
        risk=risk(),
        governance=governance(),
    )

    assert record.state is ExecutionState.FILLED
    assert record.order.requested_entry_price == Decimal("1.1000")
    assert record.fill is not None
    assert record.fill.fill_price == record.order.requested_entry_price
    assert record.fill.executed_quantity == record.order.requested_quantity


def test_every_execution_transition_is_audited():
    sink = AuditSink()
    engine = ExecutionEngine(audit_port=sink, clock=lambda: TS)

    engine.submit(
        candidate=candidate(),
        decision=decision(),
        risk=risk(),
        governance=governance(),
    )

    assert [event.event_type for event in sink.events] == [
        "EXECUTION_AUTHORIZED",
        "EXECUTION_SUBMITTED",
        "EXECUTION_FILLED",
    ]
    assert [event.outcome for event in sink.events] == [
        "AUTHORIZED",
        "SUBMITTED",
        "FILLED",
    ]


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ExecutionState.AUTHORIZED, ExecutionState.SUBMITTED),
        (ExecutionState.SUBMITTED, ExecutionState.FILLED),
        (ExecutionState.SUBMITTED, ExecutionState.FAILED),
    ],
)
def test_legal_execution_transitions(current, target):
    assert ExecutionStateMachine.transition(current, target) is target


@pytest.mark.parametrize(
    ("current", "target"),
    [
        (ExecutionState.AUTHORIZED, ExecutionState.FILLED),
        (ExecutionState.AUTHORIZED, ExecutionState.FAILED),
        (ExecutionState.SUBMITTED, ExecutionState.AUTHORIZED),
        (ExecutionState.FILLED, ExecutionState.SUBMITTED),
        (ExecutionState.FAILED, ExecutionState.SUBMITTED),
        (ExecutionState.FILLED, ExecutionState.FAILED),
    ],
)
def test_illegal_execution_transitions(current, target):
    with pytest.raises(InvalidExecutionTransition):
        ExecutionStateMachine.transition(current, target)
