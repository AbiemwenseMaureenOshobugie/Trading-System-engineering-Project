"""MS-0.19 real runtime-boundary integration tests."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from threading import Event
import time

from trading_system.decision import DecisionEngine
from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    Direction,
    GovernanceRequest,
    KeyLevel,
    KeyLevelSource,
    MarketCandle,
    MarketDataQuality,
    MarketStructureState,
    ObservationDataWindow,
    ObservationIdentity,
    ObservationStatus,
    PriceZone,
    Regime,
    RiskRequest,
    SwingKind,
    QualificationContextResult,
    QualificationContextStatus,
    SwingPoint,
    Timeframe,
)
from trading_system.governance import GovernanceEngine
from trading_system.observation import (
    InMemoryObservationRepository,
    ObservationLifecycleCoordinator,
    ObservationRunner,
)
from trading_system.risk import RiskEngine
from trading_system.runtime.audit import RuntimeAuditRecord
from trading_system.runtime.config import (
    DataProviderConfig,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)
from trading_system.runtime.control import RuntimeControl
from trading_system.runtime.status import RuntimeStatus

UTC = timezone.utc
BOUNDARY = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)
NOW = BOUNDARY + timedelta(seconds=30)
WINDOW = ObservationDataWindow(
    h1_start=BOUNDARY - timedelta(hours=4),
    h1_end=BOUNDARY,
    m15_start=BOUNDARY - timedelta(hours=2),
    m15_end=BOUNDARY,
)


def candle(timeframe: Timeframe, timestamp: datetime) -> MarketCandle:
    step = timedelta(hours=1) if timeframe is Timeframe.H1 else timedelta(minutes=15)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=timeframe,
        timestamp_open=timestamp,
        timestamp_close=timestamp + step,
        open=Decimal("1.0990"),
        high=Decimal("1.1010"),
        low=Decimal("1.0980"),
        close=Decimal("1.1000"),
        source="integration-test",
    )


class Boundary:
    def latest_completed_boundary(self, *, instrument, now):
        return BOUNDARY

    def next_completed_boundary(self, *, instrument, now):
        return BOUNDARY


class History:
    def resolve(self, *, instrument, h1_boundary):
        return WINDOW


class Market:
    def get_candles(self, *, symbol, timeframe, start, end):
        return (
            candle(
                timeframe,
                BOUNDARY - (
                    timedelta(hours=1)
                    if timeframe is Timeframe.H1
                    else timedelta(minutes=15)
                ),
            ),
        )

    def get_quality(self, *, symbol, timeframe, start, end):
        return MarketDataQuality(True, True, True, 0, ("INTEGRATION",))


class Structure:
    def evaluate(self, *, candles, evaluation_cutoff):
        swing = SwingPoint(
            BOUNDARY - timedelta(hours=1),
            Decimal("1.1000"),
            SwingKind.HIGH,
        )
        return MarketStructureState(
            regime=Regime.UPTREND,
            structure_version="MS-0.1A",
            meaningful_highs=(swing,),
            meaningful_lows=(),
            controlling_level=swing,
            range_upper_boundary=None,
            range_lower_boundary=None,
            structural_events=(),
            evaluated_at=evaluation_cutoff,
        )


class Levels:
    def detect(self, *, candles, structure):
        return (
            KeyLevel(
                key_level_id="KL-INTEGRATION",
                source_types=(KeyLevelSource.VALIDATED_SWING,),
                source_zones=(
                    (
                        KeyLevelSource.VALIDATED_SWING,
                        PriceZone(Decimal("1.0980"), Decimal("1.1000")),
                    ),
                ),
                active=True,
                role=None,
                created_at=BOUNDARY,
                updated_at=BOUNDARY,
                evidence_refs=("INTEGRATION-KL",),
                state_history=("ACTIVE",),
            ),
        )


class Selector:
    def select(self, *, key_levels, structure, direction):
        return key_levels


class Confirmation:
    def evaluate(self, *, candles, structure, setup_key_level):
        return ()


class Classifier:
    def classify(self, confirmations):
        return (
            DecisionCandidate(
                decision_id="D-MS019",
                strategy_version="MS-0.3",
                symbol="EURUSD",
                direction=Direction.BUY,
                setup_type=ConfirmationType.CP1,
                setup_id="SETUP-MS019",
                signal_timestamp=BOUNDARY,
                signal_entry_price=Decimal("1.1000"),
                proposed_stop_loss=Decimal("1.0950"),
                proposed_target=Decimal("1.1100"),
                evidence_refs=("INTEGRATION-CANDIDATE",),
            ),
        )


class Qualification:
    def qualify(
        self,
        *,
        candidate,
        key_levels,
        structure,
        boundary,
        qualification_timestamp,
    ):
        return QualificationContextResult(
            status=QualificationContextStatus.AVAILABLE,
            qualification_timestamp=qualification_timestamp,
            risk_request=RiskRequest(
                candidate=candidate,
                active_key_levels=tuple(key_levels),
                setup_key_level_id="KL-INTEGRATION",
                account_equity=Decimal("10000"),
                spread=Decimal("0"),
                slippage=Decimal("0"),
                noise=Decimal("0"),
                volatility_adjustment=Decimal("0"),
                value_per_price_unit=Decimal("100000"),
            ),
            governance_request=GovernanceRequest(
                candidate=candidate,
                instrument_session_eligible=True,
                daily_trade_count=0,
                daily_loss_count=0,
            ),
            reason_codes=(),
        )


class ObservationAudit:
    def record(self, event):
        pass


class RuntimeAudit:
    def __init__(self):
        self.events = []
        self.observation_completed = Event()

    def record(self, event: RuntimeAuditRecord):
        self.events.append(event)
        if event.event_type == "RUNTIME_OBSERVATION_COMPLETED":
            self.observation_completed.set()


class Ownership:
    def __init__(self):
        self.acquired = False

    def acquire(self):
        if self.acquired:
            raise RuntimeError("already owned")
        self.acquired = True

    def release(self):
        self.acquired = False


def runtime_config():
    return RuntimeConfig(
        runtime_id="ms019-integration",
        instruments=InstrumentConfig(("EURUSD",)),
        operational_time=OperationalTimeConfig(),
        data_provider=DataProviderConfig(
            provider="integration-test",
            credential_ref="secret://integration",
            symbol_mappings=(("EURUSD", "EUR/USD"),),
        ),
        persistence=PersistenceConfig(
            repository_ref="observation-repository",
            storage_location="memory://integration",
        ),
    )


def build_runtime():
    repository = InMemoryObservationRepository()
    observation_runner = ObservationRunner(
        market_data=Market(),
        boundary_port=Boundary(),
        history_resolver=History(),
        structure_engine=Structure(),
        key_level_engine=Levels(),
        key_level_selector=Selector(),
        confirmation_engine=Confirmation(),
        setup_classifier=Classifier(),
        risk_engine=RiskEngine(),
        governance_engine=GovernanceEngine(),
        decision_engine=DecisionEngine(),
        qualification_context=Qualification(),
        repository=repository,
        audit_port=ObservationAudit(),
        methodology_versions=(
            ("market_structure", "MS-0.1A"),
            ("key_levels", "MS-0.2"),
            ("confirmation", "MS-0.3"),
            ("risk", "MS-0.4"),
            ("governance", "MS-0.5"),
            ("decision", "MS-0.6"),
            ("observation", "MS-0.14"),
        ),
        clock=lambda: NOW,
    )
    coordinator = ObservationLifecycleCoordinator(
        clock=lambda: NOW,
        boundary_port=Boundary(),
        repository=repository,
        runner=observation_runner,
    )
    audit = RuntimeAudit()
    control = RuntimeControl(
        config=runtime_config(),
        ownership=Ownership(),
        coordinator=coordinator,
        audit_port=audit,
        clock=lambda: NOW,
    )
    return control, coordinator, repository, audit


def test_scheduled_runtime_reaches_real_observation_revision_and_converges_with_manual():
    control, coordinator, repository, audit = build_runtime()

    assert coordinator.next_invocation_at(
        instrument="EURUSD",
        now=NOW,
    ) == NOW
    assert control.start() is RuntimeStatus.RUNNING

    try:
        assert audit.observation_completed.wait(timeout=2)
        stored = repository.latest(ObservationIdentity("EURUSD", BOUNDARY))
        assert stored is not None
        assert stored.revision is not None
        assert stored.status is ObservationStatus.EVALUATED
        assert stored.revision.candidate_outcomes
        assert stored.revision.candidate_outcomes[0].decision_result.status.value == "VALID"

        manual = control.invoke_manual(
            instrument="EURUSD",
            observation_boundary=BOUNDARY,
            now=NOW,
        )
        assert manual.revision is stored.revision
    finally:
        control.stop()


def test_boundary_failure_uses_runtime_failure_boundary_without_stopping_scheduler():
    control, _, _, _ = build_runtime()

    class BrokenCoordinator:
        def next_invocation_at(self, *, instrument, now):
            raise RuntimeError("boundary unavailable")

    control._coordinator = BrokenCoordinator()
    assert control.start() is RuntimeStatus.RUNNING

    try:
        time.sleep(0.05)
        assert control.status is RuntimeStatus.RUNNING
        assert control.last_failure is not None
        assert control.last_failure.failure_code == "BOUNDARY_CALCULATION_FAILED"
    finally:
        control.stop()
