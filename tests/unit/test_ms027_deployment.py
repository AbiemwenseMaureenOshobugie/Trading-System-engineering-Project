"""MS-0.27 deployment contract tests."""

from datetime import datetime, timezone

import pytest

from trading_system.domain import DecisionStatus, ExecutionState, GovernanceStatus, RiskStatus
from trading_system.runtime import (
    AuthoritativeRecord,
    DependencyHealth,
    DeploymentError,
    DependencyStatus,
    DeploymentIdentity,
    DeploymentMode,
    DuplicateExecution,
    ExecutionAuthorizationExpired,
    OperationalCapability,
    RecoveryOutcome,
    RuntimeDeploymentController,
    RuntimeLifecycleState,
    RuntimeNotReady,
)


TS = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


class Ownership:
    def __init__(self):
        self.held = False

    def acquire(self):
        if self.held:
            raise RuntimeError("already held")
        self.held = True

    def release(self):
        self.held = False


class Audit:
    def __init__(self):
        self.events = []

    def record(self, event):
        self.events.append(event)


class Dependencies:
    def __init__(self, market=DependencyStatus.AVAILABLE, broker=DependencyStatus.AVAILABLE):
        self.market = market
        self.broker = broker

    def health(self):
        return (
            DependencyHealth("market_data", self.market, True, TS),
            DependencyHealth("broker", self.broker, False, TS),
            DependencyHealth("persistence", DependencyStatus.AVAILABLE, True, TS),
            DependencyHealth("audit", DependencyStatus.AVAILABLE, True, TS),
        )


class Store:
    def __init__(self):
        self.records = []

    def append(self, record: AuthoritativeRecord):
        if any(r.record_type == record.record_type and r.record_id == record.record_id for r in self.records):
            raise RuntimeError("duplicate authoritative record")
        self.records.append(record)

    def get(self, *, record_type, record_id):
        return next((r for r in self.records if r.record_type == record_type and r.record_id == record_id), None)

    def find_by_decision(self, decision_id):
        return tuple(r for r in self.records if r.decision_id == decision_id)


def controller(mode=DeploymentMode.PAPER_TRADING, dependencies=None, store=None):
    return RuntimeDeploymentController(
        identity=DeploymentIdentity("app-1", "strategy-1", "config-1", "runtime-1"),
        mode=mode,
        ownership=Ownership(),
        state_port=store or Store(),
        audit_port=Audit(),
        dependency_port=dependencies or Dependencies(),
        clock=lambda: TS,
    )


def test_start_reaches_running_when_required_dependencies_are_healthy():
    c = controller()
    assert c.start() is RuntimeLifecycleState.RUNNING
    assert c.readiness().liveness
    assert c.readiness().ready


def test_missing_or_stale_market_data_degrades_and_blocks_new_decisions():
    c = controller(dependencies=Dependencies(market=DependencyStatus.STALE))
    assert c.start() is RuntimeLifecycleState.DEGRADED
    assert not c.capability_available(OperationalCapability.STRATEGY_DECISIONS)


def test_recovery_is_explicit_and_returns_to_running_only_after_readiness():
    dependencies = Dependencies(market=DependencyStatus.STALE)
    c = controller(dependencies=dependencies)
    assert c.start() is RuntimeLifecycleState.DEGRADED
    assert c.begin_recovery() is RuntimeLifecycleState.RECOVERING

    dependencies.market = DependencyStatus.AVAILABLE
    assert c.refresh() is RuntimeLifecycleState.RUNNING


def test_broker_is_required_only_for_broker_modes():
    c = controller(mode=DeploymentMode.PAPER_TRADING, dependencies=Dependencies(broker=DependencyStatus.UNAVAILABLE))
    assert c.start() is RuntimeLifecycleState.RUNNING
    assert c.capability_available(OperationalCapability.EXECUTION)

    c2 = controller(mode=DeploymentMode.MT5_DEMO, dependencies=Dependencies(broker=DependencyStatus.UNAVAILABLE))
    assert c2.start() is RuntimeLifecycleState.DEGRADED
    assert not c2.capability_available(OperationalCapability.EXECUTION)


def test_execution_authorization_requires_all_upstream_authorizations():
    c = controller()
    c.start()
    with pytest.raises(DeploymentError):
        c.authorize_execution(
            decision_id="D-1",
            decision_status=DecisionStatus.WAIT,
            risk_status=RiskStatus.RISK_AUTHORIZED,
            governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        )

    with pytest.raises(DeploymentError):
        c.authorize_execution(
            decision_id="D-1",
            decision_status=DecisionStatus.VALID,
            risk_status=RiskStatus.RISK_REJECTED,
            governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        )


def test_authorization_is_runtime_scoped_and_expires_on_shutdown():
    c = controller()
    c.start()
    auth = c.authorize_execution(
        decision_id="D-1",
        decision_status=DecisionStatus.VALID,
        risk_status=RiskStatus.RISK_AUTHORIZED,
        governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
    )
    c.shutdown()
    with pytest.raises(ExecutionAuthorizationExpired):
        c.submit_execution(auth)


def test_duplicate_execution_is_fail_closed():
    store = Store()
    c = controller(store=store)
    c.start()
    c.authorize_execution(
        decision_id="D-1",
        decision_status=DecisionStatus.VALID,
        risk_status=RiskStatus.RISK_AUTHORIZED,
        governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
    )
    with pytest.raises(DuplicateExecution):
        c.authorize_execution(
            decision_id="D-1",
            decision_status=DecisionStatus.VALID,
            risk_status=RiskStatus.RISK_AUTHORIZED,
            governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        )


def test_submitted_state_is_recoverable_not_assumed_failed():
    store = Store()
    c = controller(store=store)
    c.start()
    auth = c.authorize_execution(
        decision_id="D-2",
        decision_status=DecisionStatus.VALID,
        risk_status=RiskStatus.RISK_AUTHORIZED,
        governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
    )
    c.submit_execution(auth)
    assert c.recover_execution("D-2") == RecoveryOutcome(
        "D-2", ExecutionState.SUBMITTED, "RECONCILIATION_REQUIRED"
    )


def test_terminal_execution_states_are_preserved():
    store = Store()
    c = controller(store=store)
    c.start()
    c.persist_execution_state(decision_id="D-3", state=ExecutionState.FILLED, record_id="EX-3", payload={})
    c.persist_execution_state(decision_id="D-4", state=ExecutionState.FAILED, record_id="EX-4", payload={})
    assert c.recover_execution("D-3").action == "PRESERVE_FILLED"
    assert c.recover_execution("D-4").action == "PRESERVE_FAILED"


def test_shutdown_blocks_new_work_and_stops_runtime():
    c = controller()
    c.start()
    assert c.shutdown() is RuntimeLifecycleState.STOPPED
    assert not c.capability_available(OperationalCapability.STRATEGY_DECISIONS)
    with pytest.raises(RuntimeNotReady):
        c.authorize_execution(
            decision_id="D-5",
            decision_status=DecisionStatus.VALID,
            risk_status=RiskStatus.RISK_AUTHORIZED,
            governance_status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        )


def test_authoritative_records_are_append_only():
    store = Store()
    c = controller(store=store)
    c.start()
    c.persist_execution_state(decision_id="D-6", state=ExecutionState.FILLED, record_id="EX-6", payload={"source": "test"})
    with pytest.raises(RuntimeError):
        store.append(store.records[0])
