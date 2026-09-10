"""Enumerations used by the canonical domain contracts."""

from enum import StrEnum


class Timeframe(StrEnum):
    H1 = "H1"
    M15 = "M15"


class Direction(StrEnum):
    BUY = "BUY"
    SELL = "SELL"


class Regime(StrEnum):
    UPTREND = "UPTREND"
    DOWNTREND = "DOWNTREND"
    RANGE = "RANGE"
    TRANSITION = "TRANSITION"
    UNCLEAR = "UNCLEAR"


class SwingKind(StrEnum):
    HIGH = "HIGH"
    LOW = "LOW"


class KeyLevelSource(StrEnum):
    VALIDATED_SWING = "VALIDATED_SWING"
    RANGE_BOUNDARY = "RANGE_BOUNDARY"
    BREAKOUT_LEVEL = "BREAKOUT_LEVEL"
    ROLE_REVERSAL = "ROLE_REVERSAL"


class ConfirmationType(StrEnum):
    CP1 = "CP-1"
    CP2 = "CP-2"


class RiskStatus(StrEnum):
    RISK_AUTHORIZED = "RISK_AUTHORIZED"
    RISK_REJECTED = "RISK_REJECTED"


class GovernanceStatus(StrEnum):
    GOVERNANCE_AUTHORIZED = "GOVERNANCE_AUTHORIZED"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
