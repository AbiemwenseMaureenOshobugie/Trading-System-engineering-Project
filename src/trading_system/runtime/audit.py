"""Dedicated operational audit boundary for MS-0.17."""

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


@dataclass(frozen=True, slots=True)
class RuntimeAuditRecord:
    audit_id: str
    timestamp: datetime
    runtime_id: str
    event_type: str
    component: str
    reference: str | None = None
    outcome: str | None = None


class RuntimeAuditPort(Protocol):
    def record(self, event: RuntimeAuditRecord) -> None: ...
