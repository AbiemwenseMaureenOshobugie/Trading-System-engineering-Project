
"""Canonical MS-0.14 observation-domain contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import StrEnum
from typing import Optional

from .models import DecisionCandidate, DecisionResult, GovernanceResult, KeyLevel, MarketStructureState, RiskResult


class ObservationStatus(StrEnum):
    WAIT = "WAIT"
    NO_SETUP = "NO_SETUP"
    EVALUATED = "EVALUATED"
    NO_OBSERVATION = "NO_OBSERVATION"


class ObservationReason(StrEnum):
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_MARKET_DATA = "INVALID_MARKET_DATA"
    INCOMPLETE_MARKET_DATA = "INCOMPLETE_MARKET_DATA"
    NO_NEW_H1_CANDLE = "NO_NEW_H1_CANDLE"
    NO_QUALIFYING_SETUP = "NO_QUALIFYING_SETUP"


@dataclass(frozen=True, slots=True)
class ObservationIdentity:
    instrument: str
    h1_boundary_timestamp: datetime

    def __post_init__(self) -> None:
        if self.h1_boundary_timestamp.tzinfo is None:
            raise ValueError("h1_boundary_timestamp must be timezone-aware")
        if self.h1_boundary_timestamp.astimezone(timezone.utc) != self.h1_boundary_timestamp:
            raise ValueError("h1_boundary_timestamp must be UTC")


@dataclass(frozen=True, slots=True)
class ObservationDataWindow:
    h1_start: datetime
    h1_end: datetime
    m15_start: datetime
    m15_end: datetime

    def __post_init__(self) -> None:
        values = (self.h1_start, self.h1_end, self.m15_start, self.m15_end)
        if any(value.tzinfo is None for value in values):
            raise ValueError("observation data-window timestamps must be timezone-aware")
        if self.h1_start >= self.h1_end or self.m15_start >= self.m15_end:
            raise ValueError("observation data windows must be ordered")


@dataclass(frozen=True, slots=True)
class MarketDataQuality:
    """Provider-neutral quality summary for one requested data window."""

    valid: bool
    complete: bool
    sufficient: bool
    rejected_records: int
    provenance_refs: tuple[str, ...] = ()

    @property
    def invalid(self) -> bool:
        return not self.valid


@dataclass(frozen=True, slots=True)
class CandidateOutcome:
    candidate: DecisionCandidate
    risk_result: Optional[RiskResult]
    governance_result: Optional[GovernanceResult]
    decision_result: Optional[DecisionResult]


@dataclass(frozen=True, slots=True)
class ObservationRevision:
    identity: ObservationIdentity
    revision_number: int
    evaluation_timestamp: datetime
    status: ObservationStatus
    reason: str
    methodology_versions: tuple[tuple[str, str], ...]
    data_window: Optional[ObservationDataWindow]
    h1_data_reference: Optional[str]
    m15_data_reference: Optional[str]
    validation_outcome: tuple[tuple[str, str], ...]
    market_structure: Optional[MarketStructureState]
    key_levels: tuple[KeyLevel, ...]
    candidate_outcomes: tuple[CandidateOutcome, ...]
    provenance_refs: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.revision_number < 1:
            raise ValueError("revision_number must be positive")
        if self.evaluation_timestamp.tzinfo is None:
            raise ValueError("evaluation_timestamp must be timezone-aware")


@dataclass(frozen=True, slots=True)
class ObservationResult:
    """Current canonical result for one observation identity.

    NO_OBSERVATION is transient because there is no H1 boundary to identify.
    """

    status: ObservationStatus
    reason: str
    identity: Optional[ObservationIdentity] = None
    revision: Optional[ObservationRevision] = None

    def __post_init__(self) -> None:
        if self.status is ObservationStatus.NO_OBSERVATION:
            if self.identity is not None or self.revision is not None:
                raise ValueError("NO_OBSERVATION must not carry a persisted identity")
        elif self.identity is None or self.revision is None:
            raise ValueError("persisted observation results require identity and revision")
