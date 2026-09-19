"""Tests for the deterministic MS-0.6 Decision Engine."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.decision import DecisionEngine
from trading_system.domain import (
    ConfirmationType,
    DecisionRequest,
    DecisionStatus,
    DecisionCandidate,
    Direction,
    GovernanceResult,
    GovernanceStatus,
    RiskResult,
    RiskStatus,
)

TS = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def candidate() -> DecisionCandidate:
    return DecisionCandidate(
        decision_id="D-001",
        strategy_version="MS-0.5",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id="SETUP-001",
        signal_timestamp=TS,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=("E-001",),
    )


def risk(status: RiskStatus) -> RiskResult:
    return RiskResult(
        decision_id="D-001",
        requested_risk=Decimal("0.01"),
        approved_risk=Decimal("0.01") if status is RiskStatus.RISK_AUTHORIZED else None,
        position_size=Decimal("1") if status is RiskStatus.RISK_AUTHORIZED else None,
        entry_assumption=Decimal("1.1000"),
        structural_stop_loss=Decimal("1.0950"),
        final_stop_loss=Decimal("1.0949"),
        target_price=Decimal("1.1100"),
        stop_distance=Decimal("0.0051"),
        target_distance=Decimal("0.0100"),
        risk_reward=Decimal("1.96"),
        risk_amount=Decimal("100"),
        status=status,
        reason_codes=(
            "RISK_AUTHORIZED"
            if status is RiskStatus.RISK_AUTHORIZED
            else "TARGET_BELOW_MINIMUM_RR",
        ),
    )


def governance(status: GovernanceStatus) -> GovernanceResult:
    return GovernanceResult(
        decision_id="D-001",
        instrument_session_eligible=True,
        daily_trade_count=0,
        daily_loss_count=0,
        checks=("SESSION_ELIGIBLE",),
        status=status,
        reason_codes=(
            "GOVERNANCE_CONTROLS_PASSED"
            if status is GovernanceStatus.GOVERNANCE_AUTHORIZED
            else "MAX_DAILY_TRADES_REACHED",
        ),
    )


def test_no_setup():
    result = DecisionEngine().decide(
        DecisionRequest(
            candidate=None,
            strategy_pending=False,
            risk_result=None,
            governance_result=None,
        )
    )
    assert result.status is DecisionStatus.NO_SETUP


def test_wait_when_strategy_is_pending():
    result = DecisionEngine().decide(
        DecisionRequest(
            candidate=None,
            strategy_pending=True,
            risk_result=None,
            governance_result=None,
        )
    )
    assert result.status is DecisionStatus.WAIT


def test_wait_when_risk_is_pending():
    result = DecisionEngine().decide(
        DecisionRequest(candidate(), False, None, None)
    )
    assert result.status is DecisionStatus.WAIT
    assert result.reason_codes == ("RISK_PENDING",)


def test_risk_rejection_is_final():
    result = DecisionEngine().decide(
        DecisionRequest(candidate(), False, risk(RiskStatus.RISK_REJECTED), None)
    )
    assert result.status is DecisionStatus.RISK_REJECTED


def test_wait_when_governance_is_pending():
    result = DecisionEngine().decide(
        DecisionRequest(candidate(), False, risk(RiskStatus.RISK_AUTHORIZED), None)
    )
    assert result.status is DecisionStatus.WAIT
    assert result.reason_codes == ("GOVERNANCE_PENDING",)


def test_governance_block_is_final():
    result = DecisionEngine().decide(
        DecisionRequest(
            candidate(),
            False,
            risk(RiskStatus.RISK_AUTHORIZED),
            governance(GovernanceStatus.GOVERNANCE_BLOCKED),
        )
    )
    assert result.status is DecisionStatus.GOVERNANCE_BLOCKED


def test_valid_requires_risk_and_governance_authorization():
    result = DecisionEngine().decide(
        DecisionRequest(
            candidate(),
            False,
            risk(RiskStatus.RISK_AUTHORIZED),
            governance(GovernanceStatus.GOVERNANCE_AUTHORIZED),
        )
    )
    assert result.status is DecisionStatus.VALID
    assert result.decision_id == "D-001"
