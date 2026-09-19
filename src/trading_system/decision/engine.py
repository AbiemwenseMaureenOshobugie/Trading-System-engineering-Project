"""Deterministic MS-0.6 Decision Engine."""

from trading_system.domain import (
    DecisionRequest,
    DecisionResult,
    DecisionStatus,
    GovernanceStatus,
    RiskStatus,
)

DECISION_VERSION = "MS-0.6"


class DecisionEngine:
    """Aggregate upstream outcomes without introducing trading rules."""

    def decide(self, request: DecisionRequest) -> DecisionResult:
        if request.candidate is None:
            if request.strategy_pending:
                return DecisionResult(
                    decision_id=None,
                    status=DecisionStatus.WAIT,
                    reason_codes=("STRATEGY_PENDING",),
                )
            return DecisionResult(
                decision_id=None,
                status=DecisionStatus.NO_SETUP,
                reason_codes=("NO_STRATEGY_CANDIDATE",),
            )

        decision_id = request.candidate.decision_id

        if request.risk_result is None:
            return DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.WAIT,
                reason_codes=("RISK_PENDING",),
            )

        if request.risk_result.status is RiskStatus.RISK_REJECTED:
            return DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.RISK_REJECTED,
                reason_codes=request.risk_result.reason_codes,
            )

        if request.governance_result is None:
            return DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.WAIT,
                reason_codes=("GOVERNANCE_PENDING",),
            )

        if request.governance_result.status is GovernanceStatus.GOVERNANCE_BLOCKED:
            return DecisionResult(
                decision_id=decision_id,
                status=DecisionStatus.GOVERNANCE_BLOCKED,
                reason_codes=request.governance_result.reason_codes,
            )

        return DecisionResult(
            decision_id=decision_id,
            status=DecisionStatus.VALID,
            reason_codes=("RISK_AUTHORIZED", "GOVERNANCE_AUTHORIZED"),
        )


__all__ = ["DECISION_VERSION", "DecisionEngine"]
