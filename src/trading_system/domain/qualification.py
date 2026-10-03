"""Canonical qualification-context result for MS-0.23."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .enums import QualificationContextStatus
from .models import GovernanceRequest, RiskRequest


@dataclass(frozen=True, slots=True)
class QualificationContextResult:
    """Authoritative qualification context assembled at qualification time."""

    status: QualificationContextStatus
    qualification_timestamp: datetime
    risk_request: Optional[RiskRequest]
    governance_request: Optional[GovernanceRequest]
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if self.qualification_timestamp.tzinfo is None:
            raise ValueError("qualification_timestamp must be timezone-aware")

        if self.status is QualificationContextStatus.AVAILABLE:
            if self.risk_request is None or self.governance_request is None:
                raise ValueError(
                    "available qualification context requires both downstream requests"
                )
            if self.reason_codes:
                raise ValueError(
                    "available qualification context must not contain failure reasons"
                )
        else:
            if self.risk_request is not None or self.governance_request is not None:
                raise ValueError(
                    "unavailable qualification context must not contain downstream requests"
                )
            if not self.reason_codes:
                raise ValueError(
                    "unavailable qualification context requires reason codes"
                )
