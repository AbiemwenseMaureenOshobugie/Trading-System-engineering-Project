"""Tests for the deterministic MS-0.5 Governance Engine."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    Direction,
    GovernanceRequest,
    GovernanceStatus,
)
from trading_system.governance import GovernanceEngine


TS = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def candidate(symbol: str = "EURUSD") -> DecisionCandidate:
    return DecisionCandidate(
        decision_id="D-001",
        strategy_version="MS-0.4",
        symbol=symbol,
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id="SETUP-001",
        signal_timestamp=TS,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=("E-001",),
    )


def request(
    c: DecisionCandidate,
    *,
    session=True,
    daily_trades=0,
    daily_losses=0,
) -> GovernanceRequest:
    return GovernanceRequest(
        candidate=c,
        instrument_session_eligible=session,
        daily_trade_count=daily_trades,
        daily_loss_count=daily_losses,
    )


def test_authorizes_candidate_when_all_governance_controls_pass():
    result = GovernanceEngine().authorize(request(candidate()))

    assert result.status is GovernanceStatus.GOVERNANCE_AUTHORIZED
    assert result.reason_codes == ("GOVERNANCE_CONTROLS_PASSED",)


def test_blocks_instrument_outside_initial_scope():
    result = GovernanceEngine().authorize(request(candidate("USDJPY")))

    assert result.status is GovernanceStatus.GOVERNANCE_BLOCKED
    assert result.reason_codes == ("INSTRUMENT_NOT_GOVERNED",)


def test_blocks_outside_defined_session():
    result = GovernanceEngine().authorize(request(candidate(), session=False))

    assert result.status is GovernanceStatus.GOVERNANCE_BLOCKED
    assert result.reason_codes == ("OUTSIDE_GOVERNED_SESSION",)


def test_blocks_when_two_trades_have_already_occurred():
    result = GovernanceEngine().authorize(request(candidate(), daily_trades=2))

    assert result.status is GovernanceStatus.GOVERNANCE_BLOCKED
    assert result.reason_codes == ("MAX_DAILY_TRADES_REACHED",)


def test_blocks_when_two_losses_have_already_occurred():
    result = GovernanceEngine().authorize(request(candidate(), daily_losses=2))

    assert result.status is GovernanceStatus.GOVERNANCE_BLOCKED
    assert result.reason_codes == ("MAX_DAILY_LOSSES_REACHED",)


def test_reports_all_failed_controls_deterministically():
    result = GovernanceEngine().authorize(
        request(
            candidate("USDJPY"),
            session=False,
            daily_trades=2,
            daily_losses=2,
        )
    )

    assert result.status is GovernanceStatus.GOVERNANCE_BLOCKED
    assert result.reason_codes == (
        "INSTRUMENT_NOT_GOVERNED",
        "OUTSIDE_GOVERNED_SESSION",
        "MAX_DAILY_TRADES_REACHED",
        "MAX_DAILY_LOSSES_REACHED",
    )
