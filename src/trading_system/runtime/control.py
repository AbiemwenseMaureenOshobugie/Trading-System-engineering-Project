"""Externally controlled ASTER runtime lifecycle."""

from __future__ import annotations

from datetime import datetime, timezone
from threading import Condition, RLock
from typing import Callable

from trading_system.domain import ObservationResult
from trading_system.observation import ObservationLifecycleCoordinator

from .audit import RuntimeAuditPort, RuntimeAuditRecord
from .config import RuntimeConfig
from .failure import RuntimeFailure, RuntimeFailureComponent
from .ownership import RuntimeOwnership, RuntimeOwnershipError
from .status import RuntimeStatus


class RuntimeControlError(RuntimeError):
    """Raised when an invalid runtime-control operation is requested."""


class RuntimeControl:
    VERSION = "MS-0.17"

    def __init__(
        self,
        *,
        config: RuntimeConfig,
        ownership: RuntimeOwnership,
        coordinator: ObservationLifecycleCoordinator,
        audit_port: RuntimeAuditPort,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._config = config
        self._ownership = ownership
        self._coordinator = coordinator
        self._audit = audit_port
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._condition = Condition(RLock())
        self._status = RuntimeStatus.STOPPED
        self._active_invocations = 0
        self._last_failure: RuntimeFailure | None = None

    @property
    def status(self) -> RuntimeStatus:
        with self._condition:
            return self._status

    @property
    def last_failure(self) -> RuntimeFailure | None:
        with self._condition:
            return self._last_failure

    @property
    def runtime_id(self) -> str:
        return self._config.runtime_id

    def start(self) -> RuntimeStatus:
        with self._condition:
            if self._status is not RuntimeStatus.STOPPED:
                raise RuntimeControlError(
                    f"cannot start runtime from {self._status.value}"
                )
            self._status = RuntimeStatus.STARTING
            self._emit("RUNTIME_START_REQUESTED", "RUNTIME")
        try:
            self._ownership.acquire()
            self._emit("RUNTIME_OWNERSHIP_ACQUIRED", "OWNERSHIP")
            with self._condition:
                self._last_failure = None
                self._status = RuntimeStatus.RUNNING
                self._emit("RUNTIME_STARTED", "RUNTIME")
                return self._status
        except RuntimeOwnershipError as exc:
            self._fail(
                component=RuntimeFailureComponent.OWNERSHIP,
                code="OWNERSHIP_REJECTED",
                message=str(exc),
            )
            self._emit("RUNTIME_OWNERSHIP_REJECTED", "OWNERSHIP", outcome="FAILED")
            return RuntimeStatus.FAILED
        except Exception as exc:
            self._fail(
                component=RuntimeFailureComponent.RUNTIME,
                code="START_FAILED",
                message=str(exc),
            )
            return RuntimeStatus.FAILED

    def stop(self) -> RuntimeStatus:
        with self._condition:
            if self._status is RuntimeStatus.STOPPED:
                return RuntimeStatus.STOPPED
            if self._status is RuntimeStatus.FAILED:
                self._release_ownership()
                self._status = RuntimeStatus.STOPPED
                self._emit("RUNTIME_STOPPED", "RUNTIME")
                return self._status
            if self._status is not RuntimeStatus.RUNNING:
                raise RuntimeControlError(
                    f"cannot stop runtime from {self._status.value}"
                )
            self._status = RuntimeStatus.STOPPING
            self._emit("RUNTIME_STOP_REQUESTED", "RUNTIME")
            while self._active_invocations:
                self._condition.wait()
            self._release_ownership()
            self._status = RuntimeStatus.STOPPED
            self._emit("RUNTIME_STOPPED", "RUNTIME")
            return self._status

    def run_if_due(
        self, *, instrument: str, now: datetime | None = None
    ) -> ObservationResult | None:
        return self._invoke(
            operation="RUNTIME_OBSERVATION",
            instrument=instrument,
            invocation=lambda: self._coordinator.run_if_due(
                instrument=instrument, now=now
            ),
        )

    def invoke_manual(
        self,
        *,
        instrument: str,
        observation_boundary: datetime | None = None,
        now: datetime | None = None,
    ) -> ObservationResult:
        return self._invoke(
            operation="MANUAL_OBSERVATION",
            instrument=instrument,
            invocation=lambda: self._coordinator.invoke_manual(
                instrument=instrument,
                observation_boundary=observation_boundary,
                now=now,
            ),
        )

    def _invoke(
        self,
        *,
        operation: str,
        instrument: str,
        invocation: Callable[[], ObservationResult | None],
    ) -> ObservationResult | None:
        with self._condition:
            if self._status is not RuntimeStatus.RUNNING:
                raise RuntimeControlError(
                    f"{operation} requires RUNNING runtime; current={self._status.value}"
                )
            self._active_invocations += 1
            self._emit(
                "MANUAL_OBSERVATION_REQUESTED" if operation == "MANUAL_OBSERVATION" else "RUNTIME_OBSERVATION_REQUESTED",
                "RUNTIME",
                reference=instrument,
            )
        try:
            result = invocation()
            self._emit(
                "MANUAL_OBSERVATION_COMPLETED" if operation == "MANUAL_OBSERVATION" else "RUNTIME_OBSERVATION_COMPLETED",
                "COORDINATOR",
                reference=instrument,
                outcome=result.status.value if result is not None else None,
            )
            return result
        except Exception as exc:
            self._fail(
                component=RuntimeFailureComponent.COORDINATOR,
                code="OBSERVATION_INVOCATION_FAILED",
                message=str(exc),
                reference=instrument,
            )
            self._emit(
                "MANUAL_OBSERVATION_FAILED" if operation == "MANUAL_OBSERVATION" else "RUNTIME_FAILURE",
                "COORDINATOR",
                reference=instrument,
                outcome="FAILED",
            )
            raise
        finally:
            with self._condition:
                self._active_invocations -= 1
                if self._active_invocations == 0:
                    self._condition.notify_all()

    def _fail(
        self,
        *,
        component: RuntimeFailureComponent,
        code: str,
        message: str,
        reference: str | None = None,
    ) -> None:
        timestamp = self._utc(self._clock())
        failure = RuntimeFailure(
            failure_id=f"RF-{self.runtime_id}-{timestamp.isoformat()}",
            runtime_id=self.runtime_id,
            timestamp=timestamp,
            component=component,
            failure_code=code,
            message=message,
            reference=reference,
        )
        with self._condition:
            self._last_failure = failure
            self._status = RuntimeStatus.FAILED
        self._emit(
            "RUNTIME_FAILURE",
            component.value,
            reference=reference,
            outcome=code,
        )

    def _release_ownership(self) -> None:
        try:
            self._ownership.release()
        except Exception as exc:
            self._fail(
                component=RuntimeFailureComponent.OWNERSHIP,
                code="OWNERSHIP_RELEASE_FAILED",
                message=str(exc),
            )
            raise

    def _emit(
        self,
        event_type: str,
        component: str,
        *,
        reference: str | None = None,
        outcome: str | None = None,
    ) -> None:
        self._audit.record(
            RuntimeAuditRecord(
                audit_id=f"RA-{self.runtime_id}-{self._clock().isoformat()}-{event_type}",
                timestamp=self._utc(self._clock()),
                runtime_id=self.runtime_id,
                event_type=event_type,
                component=component,
                reference=reference,
                outcome=outcome,
            )
        )

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("runtime timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
