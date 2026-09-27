"""MS-0.16 observation lifecycle coordination."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable, Protocol

from trading_system.domain import ObservationIdentity, ObservationResult, ObservationStatus

MS016_VERSION = "MS-0.16"
DEFAULT_POLL_OFFSET = timedelta(seconds=30)


class OperationalClockPort(Protocol):
    def now(self) -> datetime: ...


class ObservationBoundaryPort(Protocol):
    def latest_completed_boundary(self, *, instrument: str, now: datetime) -> datetime | None: ...

    def next_completed_boundary(self, *, instrument: str, now: datetime) -> datetime | None: ...


class ObservationLifecycleRepositoryPort(Protocol):
    def latest(self, identity: ObservationIdentity) -> ObservationResult | None: ...


class ObservationRunnerPort(Protocol):
    def run(self, *, instrument: str, now: datetime | None = None, observation_boundary: datetime | None = None) -> ObservationResult: ...


@dataclass(frozen=True, slots=True)
class ObservationInvocationOpportunity:
    instrument: str
    h1_boundary: datetime
    invocation_at: datetime


class ObservationLifecycleCoordinator:
    VERSION = MS016_VERSION

    def __init__(
        self,
        *,
        clock: OperationalClockPort | Callable[[], datetime],
        boundary_port: ObservationBoundaryPort,
        repository: ObservationLifecycleRepositoryPort,
        runner: ObservationRunnerPort,
        poll_offset: timedelta = DEFAULT_POLL_OFFSET,
    ) -> None:
        if poll_offset < timedelta(0):
            raise ValueError("poll_offset must not be negative")
        self._clock = clock
        self._boundary = boundary_port
        self._repository = repository
        self._runner = runner
        self._poll_offset = poll_offset

    def opportunity(self, *, instrument: str, now: datetime | None = None) -> ObservationInvocationOpportunity | None:
        current = self._utc(now if now is not None else self._now())
        boundary = self._boundary.latest_completed_boundary(instrument=instrument, now=current)
        if boundary is None:
            return None
        boundary = self._utc(boundary)
        invocation_at = boundary + self._poll_offset
        if current < invocation_at:
            return None
        return ObservationInvocationOpportunity(instrument, boundary, invocation_at)

    def run_if_due(self, *, instrument: str, now: datetime | None = None) -> ObservationResult | None:
        opportunity = self.opportunity(instrument=instrument, now=now)
        if opportunity is None:
            return None
        return self._run_identity(opportunity, now=now)

    def invoke_manual(
        self,
        *,
        instrument: str,
        observation_boundary: datetime | None = None,
        now: datetime | None = None,
    ) -> ObservationResult:
        current = self._utc(now if now is not None else self._now())
        boundary = observation_boundary
        if boundary is None:
            boundary = self._boundary.latest_completed_boundary(instrument=instrument, now=current)
        if boundary is None:
            return self._runner.run(instrument=instrument, now=current, observation_boundary=None)
        boundary = self._utc(boundary)
        return self._run_identity(
            ObservationInvocationOpportunity(instrument, boundary, boundary + self._poll_offset),
            now=current,
        )

    def _run_identity(self, opportunity: ObservationInvocationOpportunity, *, now: datetime | None = None) -> ObservationResult:
        identity = ObservationIdentity(opportunity.instrument, opportunity.h1_boundary)
        existing = self._repository.latest(identity)
        if existing is not None and existing.status in {ObservationStatus.EVALUATED, ObservationStatus.NO_SETUP}:
            return existing
        current = self._utc(now if now is not None else self._now())
        return self._runner.run(
            instrument=opportunity.instrument,
            now=current,
            observation_boundary=opportunity.h1_boundary,
        )

    def _now(self) -> datetime:
        value = self._clock() if callable(self._clock) else self._clock.now()
        return self._utc(value)

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("operational timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)
