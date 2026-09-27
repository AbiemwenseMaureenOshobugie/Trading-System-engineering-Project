"""MS-0.14 observation-runner contract tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    DecisionRequest,
    DecisionResult,
    DecisionStatus,
    Direction,
    GovernanceRequest,
    GovernanceResult,
    GovernanceStatus,
    KeyLevel,
    KeyLevelSource,
    MarketCandle,
    MarketDataQuality,
    MarketStructureState,
    ObservationDataWindow,
    ObservationIdentity,
    ObservationReason,
    ObservationStatus,
    PriceZone,
    Regime,
    RiskRequest,
    RiskResult,
    RiskStatus,
    SwingPoint,
    SwingKind,
    Timeframe,
)
from trading_system.observation import (
    InMemoryObservationRepository,
    ObservationExecutionError,
    ObservationRunner,
)


UTC = timezone.utc
BOUNDARY = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
WINDOW = ObservationDataWindow(
    h1_start=BOUNDARY - timedelta(hours=4),
    h1_end=BOUNDARY,
    m15_start=BOUNDARY - timedelta(hours=2),
    m15_end=BOUNDARY,
)


def candle(tf: Timeframe, open_time: datetime, close: str = "1.1000") -> MarketCandle:
    step = timedelta(hours=1) if tf is Timeframe.H1 else timedelta(minutes=15)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=tf,
        timestamp_open=open_time,
        timestamp_close=open_time + step,
        open=Decimal("1.0990"),
        high=Decimal("1.1010"),
        low=Decimal("1.0980"),
        close=Decimal(close),
        source="twelve_data",
    )


def structure() -> MarketStructureState:
    swing = SwingPoint(BOUNDARY - timedelta(hours=1), Decimal("1.1000"), SwingKind.HIGH)
    return MarketStructureState(
        regime=Regime.UPTREND,
        structure_version="MS-0.1A",
        meaningful_highs=(swing,),
        meaningful_lows=(),
        controlling_level=swing,
        range_upper_boundary=None,
        range_lower_boundary=None,
        structural_events=(),
        evaluated_at=BOUNDARY,
    )


def key_level() -> KeyLevel:
    return KeyLevel(
        key_level_id="KL-1",
        source_types=(KeyLevelSource.VALIDATED_SWING,),
        source_zones=((KeyLevelSource.VALIDATED_SWING, PriceZone(Decimal("1.0980"), Decimal("1.1000"))),),
        active=True,
        role=None,
        created_at=BOUNDARY,
        updated_at=BOUNDARY,
        evidence_refs=("E-KL",),
        state_history=("ACTIVE",),
    )


def candidate(decision_id: str) -> DecisionCandidate:
    return DecisionCandidate(
        decision_id=decision_id,
        strategy_version="MS-0.3",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id=f"SETUP-{decision_id}",
        signal_timestamp=BOUNDARY,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=("E-CAND",),
    )


class Boundary:
    def __init__(self, value=BOUNDARY):
        self.value = value

    def latest_completed_boundary(self, *, instrument, now):
        return self.value


class History:
    def resolve(self, *, instrument, h1_boundary):
        return WINDOW


class Market:
    def __init__(self, quality=None):
        self.quality = quality or MarketDataQuality(True, True, True, 0, ("ING-1",))

    def get_candles(self, *, symbol, timeframe, start, end):
        return (
            (candle(Timeframe.H1, BOUNDARY - timedelta(hours=1)),)
            if timeframe is Timeframe.H1
            else (candle(Timeframe.M15, BOUNDARY - timedelta(minutes=15)),)
        )

    def get_quality(self, *, symbol, timeframe, start, end):
        return self.quality


class Structure:
    def evaluate(self, *, candles, evaluation_cutoff):
        return structure()


class Levels:
    def detect(self, *, candles, structure):
        return (key_level(),)


class Selector:
    def select(self, *, key_levels, structure, direction):
        return key_levels


class Confirmation:
    def evaluate(self, *, candles, structure, setup_key_level):
        return ()


class Classifier:
    def __init__(self, candidates=()):
        self.candidates = tuple(candidates)

    def classify(self, confirmations):
        return self.candidates


class Risk:
    def assess(self, request):
        return RiskResult(
            decision_id=request.candidate.decision_id,
            requested_risk=Decimal("0.01"),
            approved_risk=Decimal("0.01"),
            position_size=Decimal("1000"),
            entry_assumption=request.candidate.signal_entry_price,
            structural_stop_loss=Decimal("1.0950"),
            final_stop_loss=Decimal("1.0949"),
            target_price=Decimal("1.1102"),
            stop_distance=Decimal("0.0051"),
            target_distance=Decimal("0.0102"),
            risk_reward=Decimal("2"),
            risk_amount=Decimal("100"),
            status=RiskStatus.RISK_AUTHORIZED,
            reason_codes=("RISK_AUTHORIZED",),
        )


class Governance:
    def authorize(self, request):
        return GovernanceResult(
            decision_id=request.candidate.decision_id,
            instrument_session_eligible=True,
            daily_trade_count=0,
            daily_loss_count=0,
            checks=("SESSION_ELIGIBLE",),
            status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
            reason_codes=("GOVERNANCE_AUTHORIZED",),
        )


class Decision:
    def decide(self, request: DecisionRequest):
        return DecisionResult(
            decision_id=request.candidate.decision_id,
            status=DecisionStatus.VALID,
            reason_codes=("RISK_AUTHORIZED", "GOVERNANCE_AUTHORIZED"),
        )


class Context:
    def risk_request(self, *, candidate, key_levels, boundary):
        return RiskRequest(
            candidate=candidate,
            active_key_levels=tuple(key_levels),
            setup_key_level_id="KL-1",
            account_equity=Decimal("10000"),
            spread=Decimal("0"),
            slippage=Decimal("0"),
            noise=Decimal("0"),
            volatility_adjustment=Decimal("0"),
            value_per_price_unit=Decimal("100000"),
        )

    def governance_request(self, *, candidate, boundary):
        return GovernanceRequest(
            candidate=candidate,
            instrument_session_eligible=True,
            daily_trade_count=0,
            daily_loss_count=0,
        )


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


def runner(*, classifier=None, repository=None, market=None, decision=None):
    return ObservationRunner(
        market_data=market or Market(),
        boundary_port=Boundary(),
        history_resolver=History(),
        structure_engine=Structure(),
        key_level_engine=Levels(),
        key_level_selector=Selector(),
        confirmation_engine=Confirmation(),
        setup_classifier=classifier or Classifier(),
        risk_engine=Risk(),
        governance_engine=Governance(),
        decision_engine=decision or Decision(),
        qualification_context=Context(),
        repository=repository or InMemoryObservationRepository(),
        audit_port=Audit(),
        methodology_versions=(
            ("market_structure", "MS-0.1A"),
            ("key_levels", "MS-0.2"),
            ("confirmation", "MS-0.3"),
            ("risk", "MS-0.4"),
            ("governance", "MS-0.5"),
            ("decision", "MS-0.6"),
            ("observation", "MS-0.14"),
        ),
        clock=lambda: BOUNDARY + timedelta(minutes=1),
    )


def test_no_new_h1_boundary_is_transient_no_observation():
    class NoBoundary(Boundary):
        def latest_completed_boundary(self, *, instrument, now):
            return None

    r = runner()
    r._boundary_port = NoBoundary()
    result = r.run(instrument="EURUSD", now=BOUNDARY + timedelta(minutes=1))
    assert result.status is ObservationStatus.NO_OBSERVATION
    assert result.reason == ObservationReason.NO_NEW_H1_CANDLE.value


@pytest.mark.parametrize(
    ("quality", "reason"),
    [
        (MarketDataQuality(False, True, True, 1), ObservationReason.INVALID_MARKET_DATA),
        (MarketDataQuality(True, True, False, 0), ObservationReason.INSUFFICIENT_HISTORY),
        (MarketDataQuality(True, False, True, 0), ObservationReason.INCOMPLETE_MARKET_DATA),
    ],
)
def test_data_quality_failures_create_retryable_wait(quality, reason):
    repo = InMemoryObservationRepository()
    result = runner(repository=repo, market=Market(quality=quality)).run(instrument="EURUSD")
    assert result.status is ObservationStatus.WAIT
    assert result.reason == reason.value
    assert result.revision.revision_number == 1


def test_successful_evaluation_with_no_candidate_is_no_setup():
    result = runner().run(instrument="EURUSD")
    assert result.status is ObservationStatus.NO_SETUP
    assert result.reason == ObservationReason.NO_QUALIFYING_SETUP.value
    assert result.revision.market_structure is not None
    assert result.revision.key_levels


def test_multiple_candidates_are_preserved_and_qualified_independently():
    c1, c2 = candidate("D-1"), candidate("D-2")
    result = runner(classifier=Classifier((c1, c2))).run(instrument="EURUSD")

    assert result.status is ObservationStatus.EVALUATED
    assert [item.candidate.decision_id for item in result.revision.candidate_outcomes] == ["D-1", "D-2"]
    assert all(item.decision_result.status is DecisionStatus.VALID for item in result.revision.candidate_outcomes)


def test_terminal_observation_is_idempotent():
    repo = InMemoryObservationRepository()
    first = runner(classifier=Classifier((candidate("D-1"),)), repository=repo).run(instrument="EURUSD")

    class ExplodingClassifier(Classifier):
        def classify(self, confirmations):
            raise AssertionError("terminal observation was evaluated again")

    second = runner(classifier=ExplodingClassifier(), repository=repo).run(instrument="EURUSD")
    assert first.revision.revision_number == second.revision.revision_number
    assert second.revision is first.revision


def test_wait_revision_is_retryable_and_increments_revision():
    repo = InMemoryObservationRepository()
    runner(market=Market(MarketDataQuality(True, True, False, 0)), repository=repo).run(instrument="EURUSD")
    second = runner(classifier=Classifier((candidate("D-1"),)), repository=repo).run(instrument="EURUSD")

    assert second.status is ObservationStatus.EVALUATED
    assert second.revision.revision_number == 2


def test_repository_conflict_returns_canonical_latest_revision():
    repo = InMemoryObservationRepository()
    first = runner(classifier=Classifier((candidate("D-1"),)), repository=repo).run(instrument="EURUSD")

    identity = ObservationIdentity("EURUSD", BOUNDARY)
    latest = repo.latest(identity)
    assert latest is first


def test_unexpected_component_failure_raises_application_error():
    class BrokenStructure(Structure):
        def evaluate(self, *, candles, evaluation_cutoff):
            raise RuntimeError("boom")

    r = runner(classifier=Classifier((candidate("D-1"),)))
    r._structure = BrokenStructure()

    with pytest.raises(ObservationExecutionError):
        r.run(instrument="EURUSD")
