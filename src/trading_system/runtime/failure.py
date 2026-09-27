"""Structured operational runtime failures."""

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class RuntimeFailureComponent(StrEnum):
    PROVIDER = "PROVIDER"
    CLOCK = "CLOCK"
    COORDINATOR = "COORDINATOR"
    RUNNER = "RUNNER"
    PERSISTENCE = "PERSISTENCE"
    OWNERSHIP = "OWNERSHIP"
    CONFIGURATION = "CONFIGURATION"
    RUNTIME = "RUNTIME"


@dataclass(frozen=True, slots=True)
class RuntimeFailure:
    failure_id: str
    runtime_id: str
    timestamp: datetime
    component: RuntimeFailureComponent
    failure_code: str
    message: str
    reference: str | None = None
