"""Deterministic MS-0.5 governance authorization engine."""

from __future__ import annotations

from trading_system.domain import (
    GovernanceRequest,
    GovernanceResult,
    GovernanceStatus,
)

GOVERNANCE_VERSION = "MS-0.5"
MAX_DAILY_TRADES = 2
MAX_DAILY_LOSSES = 2
ALLOWED_INSTRUMENTS = frozenset({"EURUSD", "GBPUSD"})


class GovernanceEngine:
    """Apply the locked hard operational governance controls."""

    def authorize(self, request: GovernanceRequest) -> GovernanceResult:
        candidate = request.candidate
        checks: list[str] = []
        reasons: list[str] = []

        instrument_eligible = candidate.symbol.upper() in ALLOWED_INSTRUMENTS
        session_eligible = request.instrument_session_eligible
        trade_limit_satisfied = request.daily_trade_count < MAX_DAILY_TRADES
        loss_limit_satisfied = request.daily_loss_count < MAX_DAILY_LOSSES

        checks.append(
            "INSTRUMENT_ALLOWED" if instrument_eligible else "INSTRUMENT_BLOCKED"
        )
        checks.append(
            "SESSION_ELIGIBLE" if session_eligible else "SESSION_BLOCKED"
        )
        checks.append(
            "DAILY_TRADE_LIMIT_OK"
            if trade_limit_satisfied
            else "DAILY_TRADE_LIMIT_REACHED"
        )
        checks.append(
            "DAILY_LOSS_LIMIT_OK"
            if loss_limit_satisfied
            else "DAILY_LOSS_LIMIT_REACHED"
        )

        if not instrument_eligible:
            reasons.append("INSTRUMENT_NOT_GOVERNED")
        if not session_eligible:
            reasons.append("OUTSIDE_GOVERNED_SESSION")
        if not trade_limit_satisfied:
            reasons.append("MAX_DAILY_TRADES_REACHED")
        if not loss_limit_satisfied:
            reasons.append("MAX_DAILY_LOSSES_REACHED")

        authorized = not reasons

        return GovernanceResult(
            decision_id=candidate.decision_id,
            instrument_session_eligible=session_eligible,
            daily_trade_count=request.daily_trade_count,
            daily_loss_count=request.daily_loss_count,
            checks=tuple(checks),
            status=(
                GovernanceStatus.GOVERNANCE_AUTHORIZED
                if authorized
                else GovernanceStatus.GOVERNANCE_BLOCKED
            ),
            reason_codes=tuple(reasons) if reasons else ("GOVERNANCE_CONTROLS_PASSED",),
        )


__all__ = [
    "ALLOWED_INSTRUMENTS",
    "GOVERNANCE_VERSION",
    "MAX_DAILY_LOSSES",
    "MAX_DAILY_TRADES",
    "GovernanceEngine",
]
