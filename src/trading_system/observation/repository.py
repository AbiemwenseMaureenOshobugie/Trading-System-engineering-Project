
"""Observation persistence adapters for MS-0.14."""

from __future__ import annotations

from threading import RLock

from trading_system.domain import ObservationIdentity, ObservationResult, ObservationRevision


class ObservationRevisionConflict(RuntimeError):
    """Raised when an observation revision already exists."""


class InMemoryObservationRepository:
    """Reference repository enforcing identity/revision uniqueness.

    A durable adapter can implement the same repository port without changing
    the Observation Runner.
    """

    def __init__(self) -> None:
        self._lock = RLock()
        self._revisions: dict[tuple[ObservationIdentity, int], ObservationRevision] = {}

    def latest(self, identity: ObservationIdentity) -> ObservationResult | None:
        with self._lock:
            matches = [
                revision
                for (stored_identity, _), revision in self._revisions.items()
                if stored_identity == identity
            ]
            if not matches:
                return None
            revision = max(matches, key=lambda item: item.revision_number)
            return ObservationResult(
                status=revision.status,
                reason=revision.reason,
                identity=identity,
                revision=revision,
            )

    def append(self, revision: ObservationRevision) -> ObservationResult:
        key = (revision.identity, revision.revision_number)
        with self._lock:
            if key in self._revisions:
                raise ObservationRevisionConflict(
                    f"observation revision already exists: "
                    f"{revision.identity.instrument} "
                    f"{revision.identity.h1_boundary_timestamp.isoformat()} "
                    f"revision={revision.revision_number}"
                )
            self._revisions[key] = revision
            return ObservationResult(
                status=revision.status,
                reason=revision.reason,
                identity=revision.identity,
                revision=revision,
            )
