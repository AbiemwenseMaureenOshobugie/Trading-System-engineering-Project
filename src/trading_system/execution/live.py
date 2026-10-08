"""MS-0.28 live-entry authority and reconciliation services."""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Callable

from trading_system.domain import (
    BrokerOrderOutcome, BrokerOrderSnapshot, DecisionCandidate, DecisionResult,
    DecisionStatus, ExecutionState, FillClassification, GovernanceResult,
    GovernanceStatus, LiveAuthorizationStatus, LiveExecutionAuthorization,
    LiveExecutionRecord, RiskResult, RiskStatus,
)
from trading_system.runtime.audit import RuntimeAuditRecord
from trading_system.runtime.deployment import (
    DeploymentMode, ExecutionAuthorization, OperationalCapability,
)


class LiveExecutionError(RuntimeError): pass
class LiveAuthorizationError(LiveExecutionError): pass
class LiveAuthorizationConsumed(LiveAuthorizationError): pass
class BrokerOutcomeUnknown(LiveExecutionError): pass


class LiveAuthorizationController:
    """Explicit operator action that issues one scoped live authorization."""

    VERSION = "MS-0.28"

    def __init__(self, *, runtime, authorization_port, audit_port,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._runtime = runtime
        self._authorization_port = authorization_port
        self._audit = audit_port
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def issue(self, *, decision_id: str, instrument: str,
              runtime_authorization: ExecutionAuthorization,
              authorized_by: str, expires_at: datetime) -> LiveExecutionAuthorization:
        now = self._utc(self._clock())
        if self._runtime.mode is not DeploymentMode.CONTROLLED_LIVE:
            raise LiveAuthorizationError("live authorization requires CONTROLLED_LIVE mode")
        if not self._runtime.capability_available(OperationalCapability.EXECUTION):
            raise LiveAuthorizationError("live execution capability is not ready")
        if runtime_authorization.decision_id != decision_id:
            raise LiveAuthorizationError("runtime authorization decision mismatch")
        if runtime_authorization.runtime_id != self._runtime.identity.runtime_id:
            raise LiveAuthorizationError("runtime authorization runtime mismatch")
        if runtime_authorization.runtime_context_id != self._runtime.runtime_context_id:
            raise LiveAuthorizationError("runtime authorization context mismatch")
        if runtime_authorization.execution_state is not ExecutionState.AUTHORIZED:
            raise LiveAuthorizationError("runtime authorization is not active")
        expires_at = self._utc(expires_at)
        if expires_at <= now: raise LiveAuthorizationError("expires_at must be later than authorized_at")
        if not authorized_by.strip(): raise LiveAuthorizationError("authorized_by must not be blank")
        authorization = LiveExecutionAuthorization(
            authorization_id=f"LEA-{decision_id}-{now.strftime('%Y%m%dT%H%M%S%fZ')}",
            decision_id=decision_id, instrument=instrument,
            authorized_execution_mode=DeploymentMode.CONTROLLED_LIVE.value,
            runtime_id=self._runtime.identity.runtime_id,
            runtime_context_id=self._runtime.runtime_context_id or "",
            authorized_by=authorized_by, authorized_at=now, expires_at=expires_at,
            status=LiveAuthorizationStatus.ACTIVE,
        )
        self._authorization_port.issue(authorization)
        self._emit_audit(now, self._runtime.identity.runtime_id, "LIVE_AUTHORIZATION_ISSUED", authorization.authorization_id, "AUTHORIZED")
        return authorization

    def _emit_audit(self, timestamp: datetime, runtime_id: str, event_type: str, reference: str, outcome: str) -> None:
        self._audit.record(
            RuntimeAuditRecord(
                audit_id=f"RA-MS028-{reference}-{event_type}",
                timestamp=timestamp,
                runtime_id=runtime_id,
                event_type=event_type,
                component="LIVE_EXECUTION",
                reference=reference,
                outcome=outcome,
            )
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)


class LiveExecutionEngine:
    """Cross the live broker boundary only once per explicit live authorization."""

    VERSION = "MS-0.28"

    def __init__(self, *, authorization_port, broker_submission_port,
                 broker_read_port, audit_port,
                 clock: Callable[[], datetime] | None = None) -> None:
        self._authorizations = authorization_port
        self._broker = broker_submission_port
        self._broker_read = broker_read_port
        self._audit = audit_port
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def _emit_audit(self, timestamp: datetime, runtime_id: str, event_type: str, reference: str, outcome: str) -> None:
        self._audit.record(
            RuntimeAuditRecord(
                audit_id=f"RA-MS028-{reference}-{event_type}",
                timestamp=timestamp,
                runtime_id=runtime_id,
                event_type=event_type,
                component="LIVE_EXECUTION",
                reference=reference,
                outcome=outcome,
            )
        )

    def submit(self, *, candidate: DecisionCandidate, decision: DecisionResult,
               risk: RiskResult, governance: GovernanceResult,
               runtime_authorization: ExecutionAuthorization,
               live_authorization: LiveExecutionAuthorization,
               runtime_id: str, runtime_context_id: str) -> LiveExecutionRecord:
        now = self._utc(self._clock())
        self._validate(candidate, decision, risk, governance, runtime_authorization,
                       live_authorization, runtime_id, runtime_context_id, now)
        self._authorizations.consume(live_authorization.authorization_id, now=now)
        try:
            snapshot = self._broker.submit(candidate=candidate, quantity=risk.position_size or Decimal("0"))
        except Exception as exc:
            record = self._unknown_record(candidate, live_authorization, runtime_id,
                                          runtime_context_id, risk.position_size or Decimal("0"), now, str(exc))
            self._emit_audit(now, runtime_id, "LIVE_EXECUTION_UNKNOWN", record.execution_id, "SUBMITTED")
            return record
        record = self._from_snapshot(candidate, live_authorization, runtime_id,
                                     runtime_context_id, snapshot, now)
        self._emit_audit(now, runtime_id, "LIVE_EXECUTION_SUBMISSION_OUTCOME", record.execution_id, record.state.value)
        return record

    def reconcile(self, record: LiveExecutionRecord) -> LiveExecutionRecord:
        if not record.reconciliation_required: return record
        if not record.broker_order_id:
            raise LiveExecutionError("broker order id is required for read-only reconciliation")
        snapshot = self._broker_read.get_order(record.broker_order_id)
        updated = self._from_snapshot(None, None, record.runtime_id,
                                      record.runtime_context_id, snapshot,
                                      self._utc(self._clock()), existing=record)
        self._emit_audit(updated.execution_timestamp, record.runtime_id, "LIVE_EXECUTION_RECONCILED", record.execution_id, updated.state.value)
        return updated

    def _validate(self, candidate, decision, risk, governance, runtime_auth,
                  live_auth, runtime_id, runtime_context_id, now):
        if decision.decision_id != candidate.decision_id or risk.decision_id != candidate.decision_id or governance.decision_id != candidate.decision_id:
            raise LiveAuthorizationError("authorization chain decision identity mismatch")
        if decision.status is not DecisionStatus.VALID: raise LiveAuthorizationError("live execution requires VALID decision")
        if risk.status is not RiskStatus.RISK_AUTHORIZED: raise LiveAuthorizationError("live execution requires risk authorization")
        if governance.status is not GovernanceStatus.GOVERNANCE_AUTHORIZED: raise LiveAuthorizationError("live execution requires governance authorization")
        if runtime_auth.decision_id != candidate.decision_id or runtime_auth.runtime_id != runtime_id or runtime_auth.runtime_context_id != runtime_context_id:
            raise LiveAuthorizationError("runtime authorization scope mismatch")
        if runtime_auth.execution_state is not ExecutionState.AUTHORIZED: raise LiveAuthorizationError("runtime execution authorization is not active")
        if live_auth.status is not LiveAuthorizationStatus.ACTIVE: raise LiveAuthorizationConsumed("live authorization is not active")
        if not live_auth.is_valid_at(now): raise LiveAuthorizationError("live authorization is expired or not yet active")
        if live_auth.decision_id != candidate.decision_id or live_auth.instrument != candidate.symbol:
            raise LiveAuthorizationError("live authorization decision/instrument mismatch")
        if live_auth.authorized_execution_mode != DeploymentMode.CONTROLLED_LIVE.value:
            raise LiveAuthorizationError("live authorization mode mismatch")
        if live_auth.runtime_id != runtime_id or live_auth.runtime_context_id != runtime_context_id:
            raise LiveAuthorizationError("live authorization runtime scope mismatch")
        if risk.position_size is None or risk.position_size <= 0:
            raise LiveAuthorizationError("live execution requires a positive authorized quantity")

    def _from_snapshot(self, candidate, authorization, runtime_id, runtime_context_id,
                       snapshot: BrokerOrderSnapshot, now: datetime,
                       existing: LiveExecutionRecord | None = None) -> LiveExecutionRecord:
        requested = existing.requested_quantity if existing else snapshot.requested_quantity
        executed = snapshot.executed_quantity
        remaining = requested - executed
        if snapshot.outcome is BrokerOrderOutcome.FILLED and executed == requested:
            state, recon, manual = ExecutionState.FILLED, False, False
        elif snapshot.outcome in (BrokerOrderOutcome.REJECTED, BrokerOrderOutcome.CANCELLED, BrokerOrderOutcome.EXPIRED):
            state, recon, manual = ExecutionState.FAILED, False, False
        else:
            state, recon, manual = ExecutionState.SUBMITTED, True, snapshot.outcome is BrokerOrderOutcome.UNKNOWN
        classification = FillClassification.NONE if executed == 0 else FillClassification.FULL if executed == requested else FillClassification.PARTIAL
        return LiveExecutionRecord(
            execution_id=existing.execution_id if existing else f"LEX-{authorization.authorization_id}",
            decision_id=existing.decision_id if existing else candidate.decision_id,
            state=state, authorization_id=existing.authorization_id if existing else authorization.authorization_id,
            runtime_id=runtime_id, runtime_context_id=runtime_context_id,
            instrument=existing.instrument if existing else candidate.symbol,
            requested_quantity=requested, executed_quantity=executed, remaining_quantity=remaining,
            broker_order_id=snapshot.broker_order_id, broker_outcome=snapshot.outcome,
            fill_classification=classification, actual_fill_price=snapshot.fill_price,
            execution_timestamp=existing.execution_timestamp if existing else now,
            reconciliation_required=recon, manual_reconciliation_required=manual,
            failure_reason=existing.failure_reason if existing else None,
        )

    def _unknown_record(self, candidate, authorization, runtime_id, runtime_context_id,
                        quantity, now, reason):
        return LiveExecutionRecord(
            execution_id=f"LEX-{authorization.authorization_id}", decision_id=candidate.decision_id,
            state=ExecutionState.SUBMITTED, authorization_id=authorization.authorization_id,
            runtime_id=runtime_id, runtime_context_id=runtime_context_id, instrument=candidate.symbol,
            requested_quantity=quantity, executed_quantity=Decimal("0"), remaining_quantity=quantity,
            broker_order_id=None, broker_outcome=BrokerOrderOutcome.UNKNOWN,
            fill_classification=FillClassification.NONE, actual_fill_price=None,
            execution_timestamp=now, reconciliation_required=True,
            manual_reconciliation_required=True, failure_reason=reason,
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None: raise ValueError("timestamp must be timezone-aware")
        return value.astimezone(timezone.utc)
