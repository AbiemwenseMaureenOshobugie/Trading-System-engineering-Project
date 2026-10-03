"""Dedicated MS-0.23 qualification-context tests."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    Direction,
    KeyLevel,
    KeyLevelSource,
    MarketStructureState,
    PriceZone,
    QualificationContextStatus,
    Regime,
    SwingKind,
    SwingPoint,
)
from trading_system.qualification import QualificationContextAssembler
from trading_system.session import SessionIdentity, SessionPolicyResult

AT = datetime(2026, 9, 27, 10, 30, tzinfo=timezone.utc)


def candidate(*, evidence_refs=("key_level:KL-1",)) -> DecisionCandidate:
    return DecisionCandidate(
        decision_id="D-Q-1",
        strategy_version="MS-0.3",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id="SETUP-Q-1",
        signal_timestamp=AT,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=evidence_refs,
    )


def key_level(*, active=True) -> KeyLevel:
    return KeyLevel(
        key_level_id="KL-1",
        source_types=(KeyLevelSource.VALIDATED_SWING,),
        source_zones=(
            (KeyLevelSource.VALIDATED_SWING, PriceZone(Decimal("1.0980"), Decimal("1.1000"))),
        ),
        active=active,
        role=None,
        created_at=AT,
        updated_at=AT,
        evidence_refs=("E-KL",),
        state_history=("ACTIVE",),
    )


def structure() -> MarketStructureState:
    swing = SwingPoint(AT, Decimal("1.1000"), SwingKind.HIGH)
    return MarketStructureState(
        regime=Regime.UPTREND,
        structure_version="MS-0.1A",
        meaningful_highs=(swing,),
        meaningful_lows=(),
        controlling_level=swing,
        range_upper_boundary=None,
        range_lower_boundary=None,
        structural_events=(),
        evaluated_at=AT,
    )


class Account:
    def get_account_equity(self, *, at):
        return Decimal("10000")


class MarketContext:
    def get_spread(self, *, symbol, at):
        return Decimal("0.0001")


class History:
    def get_slippage(self, *, symbol, at):
        return Decimal("0.00005")

    def get_daily_trade_count(self, *, symbol, at):
        return 1

    def get_daily_loss_count(self, *, symbol, at):
        return 0


class Noise:
    def get_noise(self, *, candidate, structure, at):
        return Decimal("0.0001")


class Volatility:
    def get_volatility_adjustment(self, *, candidate, at):
        return Decimal("0.0002")


class Instrument:
    def get_value_per_price_unit(self, *, symbol, at):
        return Decimal("100000")


class SessionPolicy:
    def __init__(self, permitted=True):
        self.permitted = permitted

    def evaluate(self, timestamp_utc):
        return SessionPolicyResult(
            timestamp_utc=timestamp_utc,
            session_identity=SessionIdentity.LONDON,
            is_trading_permitted=self.permitted,
        )


class BrokenSessionPolicy:
    def evaluate(self, timestamp_utc):
        raise RuntimeError("session provider down")


def assembler(session_policy=None):
    return QualificationContextAssembler(
        account_state=Account(),
        market_execution_context=MarketContext(),
        execution_history=History(),
        noise_policy=Noise(),
        volatility_policy=Volatility(),
        instrument_specification=Instrument(),
        session_policy=session_policy,
    )


def qualify(instance, *, refs=("key_level:KL-1",), levels=(key_level(),)):
    return instance.qualify(
        candidate=candidate(evidence_refs=refs),
        key_levels=levels,
        structure=structure(),
        boundary=AT,
        qualification_timestamp=AT,
    )


def test_missing_session_policy_fails_closed():
    result = qualify(assembler())

    assert result.status is QualificationContextStatus.UNAVAILABLE
    assert result.reason_codes == ("SESSION_POLICY_UNAVAILABLE",)
    assert result.risk_request is None
    assert result.governance_request is None


def test_session_policy_failure_fails_closed():
    result = qualify(assembler(BrokenSessionPolicy()))

    assert result.status is QualificationContextStatus.UNAVAILABLE
    assert result.reason_codes == ("SESSION_POLICY_UNAVAILABLE",)


def test_available_context_consumes_authoritative_session_policy():
    result = qualify(assembler(SessionPolicy(True)))

    assert result.status is QualificationContextStatus.AVAILABLE
    assert result.risk_request is not None
    assert result.governance_request is not None
    assert result.risk_request.account_equity == Decimal("10000")
    assert result.risk_request.spread == Decimal("0.0001")
    assert result.risk_request.slippage == Decimal("0.00005")
    assert result.risk_request.noise == Decimal("0.0001")
    assert result.risk_request.volatility_adjustment == Decimal("0.0002")
    assert result.risk_request.value_per_price_unit == Decimal("100000")
    assert result.governance_request.instrument_session_eligible is True
    assert result.governance_request.daily_trade_count == 1
    assert result.governance_request.daily_loss_count == 0


def test_session_policy_false_is_passed_through_without_reinterpretation():
    result = qualify(assembler(SessionPolicy(False)))

    assert result.status is QualificationContextStatus.AVAILABLE
    assert result.governance_request is not None
    assert result.governance_request.instrument_session_eligible is False


def test_invalid_provider_value_fails_closed():
    class BadAccount:
        def get_account_equity(self, *, at):
            return Decimal("0")

    result = QualificationContextAssembler(
        account_state=BadAccount(),
        market_execution_context=MarketContext(),
        execution_history=History(),
        noise_policy=Noise(),
        volatility_policy=Volatility(),
        instrument_specification=Instrument(),
        session_policy=SessionPolicy(True),
    ).qualify(
        candidate=candidate(),
        key_levels=(key_level(),),
        structure=structure(),
        boundary=AT,
        qualification_timestamp=AT,
    )

    assert result.status is QualificationContextStatus.UNAVAILABLE
    assert result.reason_codes == ("INVALID_ACCOUNT_EQUITY",)


def test_provider_failure_fails_closed():
    class BrokenSpread:
        def get_spread(self, *, symbol, at):
            raise RuntimeError("provider down")

    result = QualificationContextAssembler(
        account_state=Account(),
        market_execution_context=BrokenSpread(),
        execution_history=History(),
        noise_policy=Noise(),
        volatility_policy=Volatility(),
        instrument_specification=Instrument(),
        session_policy=SessionPolicy(True),
    ).qualify(
        candidate=candidate(),
        key_levels=(key_level(),),
        structure=structure(),
        boundary=AT,
        qualification_timestamp=AT,
    )

    assert result.status is QualificationContextStatus.UNAVAILABLE
    assert result.reason_codes == ("QUALIFICATION_PROVIDER_UNAVAILABLE",)


def test_missing_or_ambiguous_setup_key_level_fails_closed():
    for refs, reason in [
        (("E-CAND",), "SETUP_KEY_LEVEL_REFERENCE_UNAVAILABLE"),
        (
            ("key_level:KL-1", "key_level:KL-2"),
            "SETUP_KEY_LEVEL_REFERENCE_UNAVAILABLE",
        ),
        (("key_level:KL-X",), "SETUP_KEY_LEVEL_UNAVAILABLE"),
    ]:
        result = qualify(
            assembler(SessionPolicy(True)),
            refs=refs,
        )
        assert result.status is QualificationContextStatus.UNAVAILABLE
        assert result.reason_codes == (reason,)


def test_inactive_setup_key_level_fails_closed():
    result = qualify(
        assembler(SessionPolicy(True)),
        levels=(key_level(active=False),),
    )

    assert result.status is QualificationContextStatus.UNAVAILABLE
    assert result.reason_codes == ("SETUP_KEY_LEVEL_UNAVAILABLE",)
