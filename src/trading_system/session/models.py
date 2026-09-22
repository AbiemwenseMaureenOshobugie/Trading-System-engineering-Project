"""Immutable models for the MS-0.8 session policy contract."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import SessionIdentity


@dataclass(frozen=True, slots=True)
class SessionPolicyResult:
    """Deterministic session identity and trading-eligibility result."""

    timestamp_utc: datetime
    session_identity: SessionIdentity
    is_trading_permitted: bool
    reason: Optional[str] = None

    @property
    def is_london_session(self) -> bool:
        return self.session_identity is SessionIdentity.LONDON

    @property
    def is_overlap(self) -> bool:
        return self.session_identity is SessionIdentity.LONDON_NEW_YORK_OVERLAP

    @property
    def is_asian_session(self) -> bool:
        return self.session_identity is SessionIdentity.ASIAN
