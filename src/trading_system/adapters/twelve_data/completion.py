"""Canonical candle completion boundary (MD-02)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum

from trading_system.domain import Timeframe


class CompletionResult(Enum):
    """Result of completion check."""

    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    INVALID_TIMESTAMP = "INVALID_TIMESTAMP"


@dataclass(frozen=True, slots=True)
class CompletionBoundary:
    """Immutable completion boundary calculator.

    An incomplete provider observation is never converted into MarketCandle.
    """

    observation_cutoff: datetime

    def __post_init__(self) -> None:
        if self.observation_cutoff.tzinfo is None:
            raise ValueError("observation_cutoff must be timezone-aware (UTC)")
        if self.observation_cutoff.tzinfo != timezone.utc:
            raise ValueError("observation_cutoff must be UTC")

    @classmethod
    def from_utc_now(cls) -> CompletionBoundary:
        """Create boundary from current UTC time (for live polling)."""
        return cls(observation_cutoff=datetime.now(timezone.utc))

    @classmethod
    def from_cutoff(cls, cutoff: datetime) -> CompletionBoundary:
        """Create boundary from explicit cutoff (for testing/historical)."""
        if cutoff.tzinfo is None:
            cutoff = cutoff.replace(tzinfo=timezone.utc)
        elif cutoff.tzinfo != timezone.utc:
            cutoff = cutoff.astimezone(timezone.utc)
        return cls(observation_cutoff=cutoff)

    def expected_close(self, timestamp_open: datetime, timeframe: Timeframe) -> datetime:
        """Calculate expected close timestamp for a candle."""
        if timestamp_open.tzinfo is None:
            timestamp_open = timestamp_open.replace(tzinfo=timezone.utc)
        elif timestamp_open.tzinfo != timezone.utc:
            timestamp_open = timestamp_open.astimezone(timezone.utc)

        duration = self._duration_minutes(timeframe)
        return timestamp_open + timedelta(minutes=duration)

    def is_complete(self, timestamp_open: datetime, timeframe: Timeframe) -> CompletionResult:
        """Check if a candle is complete at the observation cutoff.

        Returns COMPLETE only when timestamp_close <= observation_cutoff.
        """
        if timestamp_open.tzinfo is None:
            return CompletionResult.INVALID_TIMESTAMP

        expected_close = self.expected_close(timestamp_open, timeframe)
        if expected_close <= self.observation_cutoff:
            return CompletionResult.COMPLETE
        return CompletionResult.INCOMPLETE

    def filter_complete(
        self, candles: list[tuple[datetime, Timeframe]]
    ) -> list[tuple[datetime, Timeframe]]:
        """Filter list to only complete (timestamp_open, timeframe) pairs."""
        return [
            (ts, tf) for ts, tf in candles
            if self.is_complete(ts, tf) is CompletionResult.COMPLETE
        ]

    def _duration_minutes(self, timeframe: Timeframe) -> int:
        return {
            Timeframe.M15: 15,
            Timeframe.H1: 60,
        }[timeframe]

    def next_poll_time(self, timeframe: Timeframe) -> datetime:
        """Calculate next poll time based on boundary + poll_offset.

        This is used by the polling schedule (MD-05).
        """
        duration = self._duration_minutes(timeframe)
        boundary = self.observation_cutoff
        minutes_since_epoch = int(boundary.timestamp() // 60)
        boundary_minutes = minutes_since_epoch - (minutes_since_epoch % duration)
        next_boundary = datetime.fromtimestamp(boundary_minutes * 60, tz=timezone.utc) + timedelta(minutes=duration)
        return next_boundary