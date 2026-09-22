"""Deterministic MS-0.8 session/time policy engine."""

from __future__ import annotations

from datetime import datetime, timezone

from .enums import SessionIdentity
from .models import SessionPolicyResult

SESSION_POLICY_VERSION = "MS-0.8"


class SessionPolicyEngine:
    """Determine session identity and trading eligibility from a UTC timestamp."""

    def evaluate(self, timestamp_utc: datetime) -> SessionPolicyResult:
        if timestamp_utc.tzinfo is None:
            raise ValueError("timestamp_utc must be timezone-aware")
        if timestamp_utc.utcoffset() != timezone.utc.utcoffset(timestamp_utc):
            raise ValueError("timestamp_utc must use UTC")

        current_time = timestamp_utc.time()

        if current_time.hour >= 12 and current_time.hour < 16:
            identity = SessionIdentity.LONDON_NEW_YORK_OVERLAP
        elif current_time.hour >= 7 and current_time.hour < 16:
            identity = SessionIdentity.LONDON
        elif current_time.hour >= 0 and current_time.hour < 8:
            identity = SessionIdentity.ASIAN
        elif current_time.hour >= 12 and current_time.hour < 21:
            identity = SessionIdentity.NEW_YORK
        else:
            identity = SessionIdentity.OUTSIDE_SESSION

        weekday = timestamp_utc.weekday() < 5
        permitted = weekday and identity in {
            SessionIdentity.LONDON,
            SessionIdentity.LONDON_NEW_YORK_OVERLAP,
        }

        if permitted:
            reason = None
        elif not weekday:
            reason = "TRADING_NOT_PERMITTED_ON_WEEKEND"
        else:
            reason = "SESSION_NOT_GOVERNED_FOR_TRADING"

        return SessionPolicyResult(
            timestamp_utc=timestamp_utc,
            session_identity=identity,
            is_trading_permitted=permitted,
            reason=reason,
        )


__all__ = ["SESSION_POLICY_VERSION", "SessionPolicyEngine"]
