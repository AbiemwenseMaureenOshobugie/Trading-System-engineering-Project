"""Boundary-driven REST polling contract (MD-05).

No WebSocket. Polling scheduled around expected candle-completion boundaries.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from trading_system.domain import Timeframe
from .completion import CompletionBoundary


@dataclass(frozen=True, slots=True)
class PollingSchedule:
    """Calculates polling times based on completion boundaries.

    - Default poll_offset = 30 seconds after expected candle close
    - M15 polls after each 15-minute boundary
    - H1 polls after each hourly boundary
    - Offset is operational configuration, not a trading rule
    """

    poll_offset_seconds: int = 30

    def __post_init__(self) -> None:
        if self.poll_offset_seconds < 0:
            raise ValueError("poll_offset_seconds must be non-negative")
        if self.poll_offset_seconds > 300:
            raise ValueError("poll_offset_seconds should not exceed 300 (5 minutes)")

    def next_poll_time(self, timeframe: Timeframe, after: datetime) -> datetime:
        """Calculate the next poll time for a timeframe after the given time."""
        boundary = CompletionBoundary.from_cutoff(after)
        next_boundary = boundary.next_poll_time(timeframe)
        return next_boundary + timedelta(seconds=self.poll_offset_seconds)

    def should_poll_now(
        self,
        timeframe: Timeframe,
        now: datetime,
        last_poll: Optional[datetime] = None,
    ) -> bool:
        """Check if we should poll now for the given timeframe."""
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        if now.tzinfo != timezone.utc:
            now = now.astimezone(timezone.utc)

        boundary = CompletionBoundary.from_cutoff(now)
        expected_close = boundary.next_poll_time(timeframe) - timedelta(seconds=self.poll_offset_seconds)

        # Poll if we're past the expected close + offset
        if now >= expected_close + timedelta(seconds=self.poll_offset_seconds):
            # Also check we haven't already polled this cycle
            if last_poll is None:
                return True
            # Check if last_poll was before this cycle's expected close
            if last_poll < expected_close:
                return True
        return False

    def time_until_next_poll(self, timeframe: Timeframe, now: datetime) -> timedelta:
        """Return time until next scheduled poll."""
        next_poll = self.next_poll_time(timeframe, now)
        if next_poll <= now:
            return timedelta(0)
        return next_poll - now


@dataclass(frozen=True, slots=True)
class PollingConfig:
    """Operational polling configuration (not strategy rules)."""

    poll_offset_seconds: int = 30
    max_retries: int = 0  # MS-0.13: no automatic retry
    rate_limit_pause_seconds: int = 60
    request_timeout_seconds: float = 10.0

    def __post_init__(self) -> None:
        if self.poll_offset_seconds < 0:
            raise ValueError("poll_offset_seconds must be non-negative")
        if self.max_retries < 0:
            raise ValueError("max_retries must be non-negative")
        if self.rate_limit_pause_seconds < 0:
            raise ValueError("rate_limit_pause_seconds must be non-negative")
        if self.request_timeout_seconds <= 0:
            raise ValueError("request_timeout_seconds must be positive")