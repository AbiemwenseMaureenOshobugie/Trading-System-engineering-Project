"""Provenance and ingestion metadata (MD-06).

MarketCandle.source retains canonical provider identity.
Separate IngestionRecord preserves full retrieval context.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from trading_system.domain import Timeframe


class IngestionOutcome(Enum):
    """Outcome of an ingestion cycle."""

    SUCCESS = "SUCCESS"
    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    PERMISSION_FAILURE = "PERMISSION_FAILURE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    VALIDATION_FAILURE = "VALIDATION_FAILURE"
    NO_NEW_CANDLES = "NO_NEW_CANDLES"


@dataclass(frozen=True, slots=True)
class IngestionRecord:
    """Auditable ingestion/retrieval metadata.

    Provider-specific retrieval details belong to the ingestion/audit boundary
    and do not become H1/M15 strategy semantics.
    """

    provider: str
    provider_symbol: str
    canonical_symbol: str
    timeframe: Timeframe
    retrieval_timestamp: datetime
    observation_cutoff: datetime
    request_context: dict
    validation_outcome: IngestionOutcome
    candles_accepted: int
    candles_rejected: int
    candles_withheld_incomplete: int
    error_details: Optional[str] = None

    def __post_init__(self) -> None:
        if self.retrieval_timestamp.tzinfo is None:
            raise ValueError("retrieval_timestamp must be timezone-aware")
        if self.observation_cutoff.tzinfo is None:
            raise ValueError("observation_cutoff must be timezone-aware")
        if self.candles_accepted < 0:
            raise ValueError("candles_accepted must be non-negative")
        if self.candles_rejected < 0:
            raise ValueError("candles_rejected must be non-negative")
        if self.candles_withheld_incomplete < 0:
            raise ValueError("candles_withheld_incomplete must be non-negative")

    @property
    def is_success(self) -> bool:
        return self.validation_outcome is IngestionOutcome.SUCCESS


@dataclass(frozen=True, slots=True)
class IngestionBatch:
    """Batch of ingestion records for a single observation cycle."""

    cycle_id: str
    start_time: datetime
    end_time: datetime
    records: tuple[IngestionRecord, ...]

    def __post_init__(self) -> None:
        if self.start_time.tzinfo is None or self.end_time.tzinfo is None:
            raise ValueError("timestamps must be timezone-aware")

    @property
    def total_accepted(self) -> int:
        return sum(r.candles_accepted for r in self.records)

    @property
    def total_rejected(self) -> int:
        return sum(r.candles_rejected for r in self.records)

    @property
    def total_withheld(self) -> int:
        return sum(r.candles_withheld_incomplete for r in self.records)

    @property
    def all_success(self) -> bool:
        return all(r.is_success for r in self.records)