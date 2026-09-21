"""Deterministic MS-0.7 paper execution engine."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Callable

from trading_system.domain import (
    AuditRecord,
    DecisionCandidate,
    DecisionResult,
    DecisionStatus,
    ExecutionRecord,
    ExecutionState,
    GovernanceResult,
    GovernanceStatus,
    PaperFill,
    PaperOrder,
    RiskResult,
    RiskStatus,
)

from .state_machine import ExecutionStateMachine


class ExecutionEngine:
    """Execute an already-authorized candidate through deterministic paper execution."""

    VERSION = "MS-0.7"

    def __init__(
        self,
        *,
        audit_port,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._audit_port = audit_port
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def submit(
        self,
        *,
        candidate: DecisionCandidate,
        decision: DecisionResult,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> ExecutionRecord:
        self._assert_authorized(candidate, decision, risk, governance)

        now = self._clock()
        execution_id = f"EX-{candidate.decision_id}"
        order_id = f"PO-{candidate.decision_id}"
        fill_id = f"PF-{candidate.decision_id}"

        self._audit(
            audit_id=f"{execution_id}-AUTHORIZED",
            timestamp=now,
            decision_id=candidate.decision_id,
            event_type="EXECUTION_AUTHORIZED",
            outcome=ExecutionState.AUTHORIZED.value,
            payload_refs=(execution_id,),
        )

        order = PaperOrder(
            order_id=order_id,
            decision_id=candidate.decision_id,
            symbol=candidate.symbol,
            direction=candidate.direction,
            requested_entry_price=candidate.signal_entry_price,
            requested_quantity=risk.position_size,
            submission_timestamp=now,
        )
        state = ExecutionStateMachine.transition(
            ExecutionState.AUTHORIZED, ExecutionState.SUBMITTED
        )
        self._audit(
            audit_id=f"{execution_id}-SUBMITTED",
            timestamp=now,
            decision_id=candidate.decision_id,
            event_type="EXECUTION_SUBMITTED",
            outcome=state.value,
            payload_refs=(execution_id, order_id),
        )

        fill = PaperFill(
            fill_id=fill_id,
            order_id=order_id,
            fill_price=order.requested_entry_price,
            executed_quantity=order.requested_quantity,
            execution_timestamp=now,
        )
        state = ExecutionStateMachine.transition(state, ExecutionState.FILLED)
        self._audit(
            audit_id=f"{execution_id}-FILLED",
            timestamp=now,
            decision_id=candidate.decision_id,
            event_type="EXECUTION_FILLED",
            outcome=state.value,
            payload_refs=(execution_id, order_id, fill_id),
        )

        return ExecutionRecord(
            execution_id=execution_id,
            decision_id=candidate.decision_id,
            state=state,
            order_id=order_id,
            fill_id=fill_id,
            order=order,
            fill=fill,
            failure_reason=None,
        )

    @staticmethod
    def _assert_authorized(
        candidate: DecisionCandidate,
        decision: DecisionResult,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> None:
        if decision.decision_id != candidate.decision_id:
            raise PermissionError("decision_id does not match candidate")
        if risk.decision_id != candidate.decision_id:
            raise PermissionError("risk decision_id does not match candidate")
        if governance.decision_id != candidate.decision_id:
            raise PermissionError("governance decision_id does not match candidate")
        if decision.status is not DecisionStatus.VALID:
            raise PermissionError("execution requires VALID decision")
        if risk.status is not RiskStatus.RISK_AUTHORIZED:
            raise PermissionError("execution requires risk authorization")
        if governance.status is not GovernanceStatus.GOVERNANCE_AUTHORIZED:
            raise PermissionError("execution requires governance authorization")
        if risk.position_size is None or risk.position_size <= 0:
            raise PermissionError("execution requires a positive authorized position size")

    def _audit(
        self,
        *,
        audit_id: str,
        timestamp: datetime,
        decision_id: str,
        event_type: str,
        outcome: str,
        payload_refs: tuple[str, ...],
    ) -> None:
        self._audit_port.record(
            AuditRecord(
                audit_id=audit_id,
                timestamp=timestamp,
                event_type=event_type,
                strategy_version=self.VERSION,
                decision_id=decision_id,
                payload_refs=payload_refs,
                outcome=outcome,
            )
        )
