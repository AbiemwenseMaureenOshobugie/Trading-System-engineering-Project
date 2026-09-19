"""Tests for the deterministic MS-0.4 Risk Engine."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    Direction,
    KeyLevel,
    KeyLevelSource,
    PriceZone,
    RiskRequest,
    RiskStatus,
)
from trading_system.risk import RiskEngine


TS = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def candidate(
    direction: Direction,
    entry: str,
    structural_sl: str,
) -> DecisionCandidate:
    return DecisionCandidate(
        decision_id="D-001",
        strategy_version="MS-0.3",
        symbol="EURUSD",
        direction=direction,
        setup_type=ConfirmationType.CP1,
        setup_id="SETUP-001",
        signal_timestamp=TS,
        signal_entry_price=Decimal(entry),
        proposed_stop_loss=Decimal(structural_sl),
        proposed_target=None,
        evidence_refs=("E-001",),
    )


def key_level(
    key_level_id: str,
    lower: str,
    upper: str,
) -> KeyLevel:
    zone = PriceZone(Decimal(lower), Decimal(upper))
    return KeyLevel(
        key_level_id=key_level_id,
        source_types=(KeyLevelSource.VALIDATED_SWING,),
        source_zones=((KeyLevelSource.VALIDATED_SWING, zone),),
        active=True,
        role=None,
        created_at=TS,
        updated_at=TS,
        evidence_refs=(),
        state_history=("ACTIVE",),
    )


def request(
    c: DecisionCandidate,
    *,
    levels=(),
    setup_key_level_id=None,
    equity="10000",
    spread="0.0001",
    slippage="0",
    noise="0",
    volatility_adjustment="0",
    value_per_price_unit="100000",
) -> RiskRequest:
    return RiskRequest(
        candidate=c,
        active_key_levels=tuple(levels),
        setup_key_level_id=setup_key_level_id,
        account_equity=Decimal(equity),
        spread=Decimal(spread),
        slippage=Decimal(slippage),
        noise=Decimal(noise),
        volatility_adjustment=Decimal(volatility_adjustment),
        value_per_price_unit=Decimal(value_per_price_unit),
    )


def test_buy_uses_nearest_opposing_source_zone_boundary_when_rr_is_at_least_2():
    c = candidate(Direction.BUY, "1.1000", "1.0950")
    result = RiskEngine().assess(
        request(
            c,
            levels=(
                key_level("KL-NEAR", "1.1120", "1.1150"),
                key_level("KL-FAR", "1.1300", "1.1350"),
            ),
        )
    )

    assert result.status is RiskStatus.RISK_AUTHORIZED
    assert result.final_stop_loss == Decimal("1.0949")
    assert result.target_price == Decimal("1.1120")
    assert result.risk_reward > Decimal("2")


def test_buy_rejects_nearest_opposing_boundary_below_2r():
    c = candidate(Direction.BUY, "1.1000", "1.0950")
    result = RiskEngine().assess(
        request(c, levels=(key_level("KL-NEAR", "1.1090", "1.1120"),))
    )

    assert result.status is RiskStatus.RISK_REJECTED
    assert result.reason_codes == ("TARGET_BELOW_MINIMUM_RR",)


def test_buy_falls_back_to_exact_2r_when_no_opposing_boundary_exists():
    c = candidate(Direction.BUY, "1.1000", "1.0950")
    result = RiskEngine().assess(request(c))

    assert result.status is RiskStatus.RISK_AUTHORIZED
    assert result.target_price == Decimal("1.1102")


def test_sell_uses_nearest_opposing_source_zone_boundary():
    c = candidate(Direction.SELL, "1.1000", "1.1050")
    result = RiskEngine().assess(
        request(
            c,
            levels=(
                key_level("KL-NEAR", "1.0850", "1.0880"),
                key_level("KL-FAR", "1.0700", "1.0750"),
            ),
        )
    )

    assert result.status is RiskStatus.RISK_AUTHORIZED
    assert result.final_stop_loss == Decimal("1.1051")
    assert result.target_price == Decimal("1.0880")
    assert result.risk_reward > Decimal("2")


def test_execution_buffer_is_spread_plus_slippage_plus_noise_plus_volatility_adjustment():
    c = candidate(Direction.BUY, "1.1000", "1.0950")
    result = RiskEngine().assess(
        request(
            c,
            spread="0.0002",
            slippage="0.0001",
            noise="0.0003",
            volatility_adjustment="0.0004",
        )
    )

    assert result.final_stop_loss == Decimal("1.0940")
    assert result.stop_distance == Decimal("0.0060")


def test_risk_is_fixed_at_one_percent_and_position_size_uses_monetary_risk():
    c = candidate(Direction.BUY, "1.1000", "1.0951")
    result = RiskEngine().assess(
        request(
            c,
            equity="10000",
            value_per_price_unit="100000",
            spread="0.0001",
        )
    )

    assert result.requested_risk == Decimal("0.01")
    assert result.approved_risk == Decimal("0.01")
    assert result.risk_amount == Decimal("100.00")
    assert result.position_size == Decimal("0.2")
