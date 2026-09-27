"""Provider-neutral operational helpers for MS-0.14."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from trading_system.application.ports import MarketDataPort
from trading_system.domain import ObservationDataWindow, Timeframe


class MarketDataH1BoundaryResolver:
    """Resolve the newest completed H1 boundary from canonical market data."""

    def __init__(self, market_data: MarketDataPort, lookback: timedelta = timedelta(hours=2)) -> None:
        self._market_data = market_data
        self._lookback = lookback

    def latest_completed_boundary(self, *, instrument: str, now: datetime) -> datetime | None:
        if now.tzinfo is None:
            raise ValueError("now must be timezone-aware")
        now = now.astimezone(timezone.utc)
        candles = self._market_data.get_candles(
            symbol=instrument,
            timeframe=Timeframe.H1,
            start=now - self._lookback,
            end=now,
        )
        completed = [c.timestamp_close for c in candles if c.timestamp_close <= now]
        return max(completed) if completed else None

    def next_completed_boundary(self, *, instrument: str, now: datetime) -> datetime | None:
        current = now.astimezone(timezone.utc)
        latest = self.latest_completed_boundary(instrument=instrument, now=current)
        if latest is not None:
            return latest + timedelta(hours=1)
        return current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)


class ExplicitObservationHistoryResolver:
    """Resolve an operational data window supplied by the application.

    The resolver owns no fixed strategy lookback. The caller supplies the
    window policy appropriate to the installed deterministic engines.
    """

    def __init__(self, resolver: Callable[[str, datetime], ObservationDataWindow]) -> None:
        self._resolver = resolver

    def resolve(self, *, instrument: str, h1_boundary: datetime) -> ObservationDataWindow:
        return self._resolver(instrument, h1_boundary)
