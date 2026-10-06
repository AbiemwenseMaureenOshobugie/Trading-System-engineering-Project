"""Platform-neutral MS-0.27 production deployment contract.

This module owns deployment/runtime safety boundaries only. It does not own
strategy, risk, governance, broker mechanics, or market-microstructure rules.
Concrete persistence, secret-management, deployment, monitoring, and broker
adapters remain outside this module.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Callable, Mapping, Protocol, Sequence

from trading_system.domain import DecisionStatus, ExecutionState, GovernanceStatus, RiskStatus
from trading_system.runtime.audit import RuntimeAuditPort, RuntimeAuditRecord
from trading_system.runtime.ownership import RuntimeOwnership


class DeploymentMode(StrEnum):
    DECISION_SUPPORT = "DECISION_SUPPORT"
    PAPER_TRADING = "PAPER_TRADING"
    MT5_DEMO = "MT5_DEMO"
    CONTROLLED_LIVE = "CONTROLLED_LIVE"


class RuntimeLifecycleState(StrEnum):
    STARTING = "STARTING"
    INITIALIZING = "INITIALIZING"
    RUNNING = "RUNNING"
    DEGRADED = "DEGRADED"
    RECOVERING = "RECOVERING"
    SHUTTING_DOWN = "SHUTTING_DOWN"
    STOPPED = "STOPPED"


class DependencyStatus(StrEnum):
    AVAILABLE = "AVAILABLE"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"


class OperationalCapability(StrEnum):
    STRATEGY_DECISIONS = "STRATEGY_DECISIONS"
    EXECUTION = "EXECUTION"


class DeploymentError(RuntimeError):
    """Base error for MS-0.27 deployment-boundary failures."""


class RuntimeNotReady(DeploymentError):
    """Raised when an operation requires a ready runtime."""


class DuplicateExecution(DeploymentError):
    """Raised when a decision already has authoritative execution history."""


class ExecutionAuthorizationExpired(DeploymentError):
    """Raised when an authorization belongs to an old runtime context."""


@dataclass(frozen=True, slots=True)
class DeploymentIdentity:
    """Version identity required to interpret one deployment/runtime instance."""

    application_version: str
    strategy_version: str
    configuration_version: str
    runtime_id: str

    def __post_init__(self) -> None:
        for name, value in (
            ("application_version", self.application_version),
            ("strategy_version", self.strategy_version),
            ("configuration_version", self.configuration_version),
            ("runtime_id", self.runtime_id),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be blank")


@dataclass(frozen=True, slots=True)
class DependencyHealth:
    """Current health/currency of one external capability."""

    name: str
    status: DependencyStatus
    required: bool
    checked_at: datetime
    detail: str = ""

    def __post_init__(self) -> None:
        if not self.name.strip():
            raise ValueError("dependency name must not be blank")
        if self.checked_at.tzinfo is None:
            raise ValueError("dependency checked_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RuntimeReadiness:
    """Derived readiness view; it is never the authoritative historical record."""

    liveness: bool
    ready: bool
    dependencies: tuple[DependencyHealth, ...]
    reasons: tuple[str, ...]

    @property
    def required_dependencies_healthy(self) -> bool:
        return all(
            dependency.status is DependencyStatus.AVAILABLE
            for dependency in self.dependencies
            if dependency.required
        )


@dataclass(frozen=True, slots=True)
class AuthoritativeRecord:
    """Opaque durable record owned by an implementation of OperationalStatePort."""

    record_type: str
    record_id: str
    decision_id: str | None
    state: str
    created_at: datetime
    identity: DeploymentIdentity
    payload: Mapping[str, object]

    def __post_init__(self) -> None:
        if not self.record_type.strip() or not self.record_id.strip():
            raise ValueError("record type and id must not be blank")
        if self.created_at.tzinfo is None:
            raise ValueError("created_at must be timezone-aware")


class OperationalStatePort(Protocol):
    """Durable append-only boundary for authoritative operational state.

    The adapter decides how and where records are durably stored. MS-0.27 does
    not select a persistence technology.
    """

    def append(self, record: AuthoritativeRecord) -> None: ...

    def get(self, *, record_type: str, record_id: str) -> AuthoritativeRecord | None: ...

    def find_by_decision(self, decision_id: str) -> Sequence[AuthoritativeRecord]: ...


class DependencyHealthPort(Protocol):
    """Supply current dependency health without owning deployment policy."""

    def health(self) -> Sequence[DependencyHealth]: ...


@dataclass(frozen=True, slots=True)
class ExecutionAuthorization:
    """Runtime-scoped execution authorization envelope.

    The underlying Decision/Risk/Governance authorizations remain authoritative.
    This envelope only binds that already-authorized decision to one live
    runtime context.
    """

    decision_id: str
    runtime_id: str
    runtime_context_id: str
    issued_at: datetime
    execution_state: ExecutionState = ExecutionState.AUTHORIZED

    def __post_init__(self) -> None:
        if self.issued_at.tzinfo is None:
            raise ValueError("issued_at must be timezone-aware")


@dataclass(frozen=True, slots=True)
class RecoveryOutcome:
    """Deterministic interpretation of persisted execution state after restart."""

    decision_id: str
    state: ExecutionState
    action: str


class RuntimeDeploymentController:
    """Own the MS-0.27 runtime lifecycle and fail-closed operational gates."""

    VERSION = "MS-0.27"

    def __init__(
        self,
        *,
        identity: DeploymentIdentity,
        mode: DeploymentMode,
        ownership: RuntimeOwnership,
        state_port: OperationalStatePort,
        audit_port: RuntimeAuditPort,
        dependency_port: DependencyHealthPort,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self.identity = identity
        self.mode = mode
        self._ownership = ownership
        self._state_port = state_port
        self._audit = audit_port
        self._dependency_port = dependency_port
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._state = RuntimeLifecycleState.STOPPED
        self._runtime_context_id: str | None = None
        self._context_sequence = 0

    @property
    def state(self) -> RuntimeLifecycleState:
        return self._state

    @property
    def runtime_context_id(self) -> str | None:
        return self._runtime_context_id

    def start(self) -> RuntimeLifecycleState:
        if self._state is not RuntimeLifecycleState.STOPPED:
            raise DeploymentError(f"cannot start from {self._state.value}")

        self._transition(RuntimeLifecycleState.STARTING)
        self._ownership.acquire()
        try:
            self._transition(RuntimeLifecycleState.INITIALIZING)
            self._context_sequence += 1
            self._runtime_context_id = (
                f"{self.identity.runtime_id}:{self._context_sequence}"
            )
            readiness = self.readiness()
            if readiness.ready:
                self._transition(RuntimeLifecycleState.RUNNING)
            else:
                self._transition(RuntimeLifecycleState.DEGRADED)
            return self._state
        except Exception:
            self._runtime_context_id = None
            self._ownership.release()
            self._state = RuntimeLifecycleState.STOPPED
            raise

    def refresh(self) -> RuntimeLifecycleState:
        """Re-evaluate dependencies and enter RECOVERING only during recovery."""

        if self._state not in (
            RuntimeLifecycleState.RUNNING,
            RuntimeLifecycleState.DEGRADED,
            RuntimeLifecycleState.RECOVERING,
        ):
            raise DeploymentError(f"cannot refresh from {self._state.value}")

        readiness = self.readiness()
        if self._state is RuntimeLifecycleState.RECOVERING:
            if readiness.ready:
                self._transition(RuntimeLifecycleState.RUNNING)
        elif self._state is RuntimeLifecycleState.RUNNING and not readiness.ready:
            self._transition(RuntimeLifecycleState.DEGRADED)
        return self._state

    def begin_recovery(self) -> RuntimeLifecycleState:
        if self._state is not RuntimeLifecycleState.DEGRADED:
            raise DeploymentError(f"recovery requires DEGRADED; current={self._state.value}")
        self._transition(RuntimeLifecycleState.RECOVERING)
        return self._state

    def shutdown(self) -> RuntimeLifecycleState:
        if self._state is RuntimeLifecycleState.STOPPED:
            return self._state
        self._transition(RuntimeLifecycleState.SHUTTING_DOWN)
        # The persistence adapter is responsible for making prior authoritative
        # records durable before ownership is released. No new work is allowed.
        self._runtime_context_id = None
        self._ownership.release()
        self._transition(RuntimeLifecycleState.STOPPED)
        return self._state

    def readiness(self) -> RuntimeReadiness:
        dependencies = tuple(self._dependency_port.health())
        reasons: list[str] = []

        for dependency in dependencies:
            if dependency.required and dependency.status is not DependencyStatus.AVAILABLE:
                reasons.append(
                    f"REQUIRED_DEPENDENCY_{dependency.status.value}:{dependency.name}"
                )

        if not self._has_required_market_data(dependencies):
            reasons.append("MARKET_DATA_NOT_CURRENT")

        if self.mode in (DeploymentMode.MT5_DEMO, DeploymentMode.CONTROLLED_LIVE):
            if not self._has_available(dependencies, "broker"):
                reasons.append("BROKER_UNAVAILABLE")

        return RuntimeReadiness(
            liveness=self._state is not RuntimeLifecycleState.STOPPED,
            ready=not reasons,
            dependencies=dependencies,
            reasons=tuple(reasons),
        )

    def capability_available(self, capability: OperationalCapability) -> bool:
        if self._state is not RuntimeLifecycleState.RUNNING:
            return False
        readiness = self.readiness()
        if not readiness.ready:
            return False
        if capability is OperationalCapability.STRATEGY_DECISIONS:
            return self._has_available(readiness.dependencies, "market_data")
        if capability is OperationalCapability.EXECUTION:
            if self.mode in (DeploymentMode.MT5_DEMO, DeploymentMode.CONTROLLED_LIVE):
                return self._has_available(readiness.dependencies, "broker")
            return True
        return False

    def authorize_execution(
        self,
        *,
        decision_id: str,
        decision_status: DecisionStatus,
        risk_status: RiskStatus,
        governance_status: GovernanceStatus,
    ) -> ExecutionAuthorization:
        if not self.capability_available(OperationalCapability.EXECUTION):
            raise RuntimeNotReady("execution capability is not ready")
        if decision_status is not DecisionStatus.VALID:
            raise DeploymentError("execution requires VALID decision")
        if risk_status is not RiskStatus.RISK_AUTHORIZED:
            raise DeploymentError("execution requires risk authorization")
        if governance_status is not GovernanceStatus.GOVERNANCE_AUTHORIZED:
            raise DeploymentError("execution requires governance authorization")
        if self._state_port.find_by_decision(decision_id):
            raise DuplicateExecution(
                f"decision already has authoritative execution history: {decision_id}"
            )
        if self._runtime_context_id is None:
            raise RuntimeNotReady("runtime execution context is unavailable")

        now = self._utc(self._clock())
        authorization = ExecutionAuthorization(
            decision_id=decision_id,
            runtime_id=self.identity.runtime_id,
            runtime_context_id=self._runtime_context_id,
            issued_at=now,
        )
        self._state_port.append(
            AuthoritativeRecord(
                record_type="execution",
                record_id=f"EXAUTH-{decision_id}",
                decision_id=decision_id,
                state=ExecutionState.AUTHORIZED.value,
                created_at=now,
                identity=self.identity,
                payload={"runtime_context_id": self._runtime_context_id},
            )
        )
        return authorization

    def submit_execution(self, authorization: ExecutionAuthorization) -> None:
        """Persist SUBMITTED only for the current runtime authorization context."""

        self._assert_current_authorization(authorization)
        now = self._utc(self._clock())
        self._state_port.append(
            AuthoritativeRecord(
                record_type="execution",
                record_id=f"EXSUB-{authorization.decision_id}",
                decision_id=authorization.decision_id,
                state=ExecutionState.SUBMITTED.value,
                created_at=now,
                identity=self.identity,
                payload={"runtime_context_id": authorization.runtime_context_id},
            )
        )

    def recover_execution(self, decision_id: str) -> RecoveryOutcome | None:
        records = tuple(self._state_port.find_by_decision(decision_id))
        if not records:
            return None

        state = ExecutionState(records[-1].state)
        if state is ExecutionState.AUTHORIZED:
            return RecoveryOutcome(
                decision_id=decision_id,
                state=state,
                action="EXPIRED_AUTHORIZATION_REQUIRES_NEW_EVALUATION",
            )
        if state is ExecutionState.SUBMITTED:
            return RecoveryOutcome(
                decision_id=decision_id,
                state=state,
                action="RECONCILIATION_REQUIRED",
            )
        if state is ExecutionState.FILLED:
            return RecoveryOutcome(
                decision_id=decision_id,
                state=state,
                action="PRESERVE_FILLED",
            )
        return RecoveryOutcome(
            decision_id=decision_id,
            state=state,
            action="PRESERVE_FAILED",
        )

    def persist_execution_state(
        self,
        *,
        decision_id: str,
        state: ExecutionState,
        record_id: str,
        payload: Mapping[str, object],
    ) -> None:
        """Append authoritative execution state; existing history is immutable."""

        if state is ExecutionState.AUTHORIZED:
            raise DeploymentError(
                "use authorize_execution to create runtime-scoped AUTHORIZED state"
            )
        self._state_port.append(
            AuthoritativeRecord(
                record_type="execution",
                record_id=record_id,
                decision_id=decision_id,
                state=state.value,
                created_at=self._utc(self._clock()),
                identity=self.identity,
                payload=payload,
            )
        )

    def _assert_current_authorization(self, authorization: ExecutionAuthorization) -> None:
        if authorization.runtime_id != self.identity.runtime_id:
            raise ExecutionAuthorizationExpired("authorization belongs to another runtime")
        if authorization.runtime_context_id != self._runtime_context_id:
            raise ExecutionAuthorizationExpired("authorization belongs to an expired runtime context")
        if authorization.execution_state is not ExecutionState.AUTHORIZED:
            raise DeploymentError("execution authorization is no longer SUBMITTABLE")
        if not self.capability_available(OperationalCapability.EXECUTION):
            raise RuntimeNotReady("execution capability is no longer ready")

    @staticmethod
    def _has_available(
        dependencies: Sequence[DependencyHealth], name: str
    ) -> bool:
        return any(
            dependency.name == name
            and dependency.status is DependencyStatus.AVAILABLE
            for dependency in dependencies
        )

    @classmethod
    def _has_required_market_data(
        cls, dependencies: Sequence[DependencyHealth]
    ) -> bool:
        return cls._has_available(dependencies, "market_data")

    def _transition(self, target: RuntimeLifecycleState) -> None:
        allowed = {
            RuntimeLifecycleState.STARTING: {RuntimeLifecycleState.INITIALIZING},
            RuntimeLifecycleState.INITIALIZING: {
                RuntimeLifecycleState.RUNNING,
                RuntimeLifecycleState.DEGRADED,
            },
            RuntimeLifecycleState.RUNNING: {
                RuntimeLifecycleState.DEGRADED,
                RuntimeLifecycleState.SHUTTING_DOWN,
            },
            RuntimeLifecycleState.DEGRADED: {
                RuntimeLifecycleState.RECOVERING,
                RuntimeLifecycleState.SHUTTING_DOWN,
            },
            RuntimeLifecycleState.RECOVERING: {
                RuntimeLifecycleState.RUNNING,
                RuntimeLifecycleState.DEGRADED,
                RuntimeLifecycleState.SHUTTING_DOWN,
            },
            RuntimeLifecycleState.SHUTTING_DOWN: {RuntimeLifecycleState.STOPPED},
            RuntimeLifecycleState.STOPPED: {RuntimeLifecycleState.STARTING},
        }
        if target not in allowed[self._state]:
            raise DeploymentError(
                f"invalid runtime transition: {self._state.value} -> {target.value}"
            )
        self._state = target
        self._audit.record(
            RuntimeAuditRecord(
                audit_id=f"RA-{self.identity.runtime_id}-{self._utc(self._clock()).isoformat()}-{target.value}",
                timestamp=self._utc(self._clock()),
                runtime_id=self.identity.runtime_id,
                event_type="RUNTIME_STATE_CHANGED",
                component="DEPLOYMENT",
                outcome=target.value,
            )
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("runtime timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
