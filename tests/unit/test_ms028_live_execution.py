"""MS-0.28 live execution contract tests."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_system.domain import (
    BrokerOrderOutcome, BrokerOrderSnapshot, BrokerSubmissionResult, ConfirmationType, DecisionCandidate,
    DecisionResult, DecisionStatus, Direction, ExecutionState, FillClassification,
    GovernanceResult, GovernanceStatus, LiveAuthorizationStatus, RiskResult, RiskStatus,
)
from trading_system.execution.live import (
    LiveAuthorizationController, LiveAuthorizationConsumed, LiveExecutionEngine,
)
from trading_system.runtime import (
    DeploymentIdentity, DeploymentMode, ExecutionAuthorization,
    RuntimeDeploymentController, RuntimeLifecycleState,
)

NOW = datetime(2026, 10, 7, 10, 0, tzinfo=timezone.utc)

class Ownership:
    def acquire(self): pass
    def release(self): pass

class Audit:
    def __init__(self): self.events = []
    def record(self, event): self.events.append(event)

class Dependencies:
    def health(self):
        from trading_system.runtime import DependencyHealth, DependencyStatus
        return (
            DependencyHealth("market_data", DependencyStatus.AVAILABLE, True, NOW),
            DependencyHealth("broker", DependencyStatus.AVAILABLE, False, NOW),
            DependencyHealth("persistence", DependencyStatus.AVAILABLE, True, NOW),
            DependencyHealth("audit", DependencyStatus.AVAILABLE, True, NOW),
        )

class Store:
    def __init__(self): self.items = {}
    def issue(self, authorization):
        if authorization.authorization_id in self.items: raise RuntimeError("duplicate")
        self.items[authorization.authorization_id] = authorization
        return authorization
    def get(self, authorization_id): return self.items.get(authorization_id)
    def consume(self, authorization_id, *, now):
        a = self.items[authorization_id]
        if a.status is not LiveAuthorizationStatus.ACTIVE: raise LiveAuthorizationConsumed("consumed")
        if not a.is_valid_at(now): raise LiveAuthorizationConsumed("expired")
        a = replace(a, status=LiveAuthorizationStatus.CONSUMED)
        self.items[authorization_id] = a
        return a

class Broker:
    def __init__(self, outcome=BrokerOrderOutcome.FILLED): self.outcome = outcome; self.calls = 0
    def submit(self, request):
        self.calls += 1
        quantity = request.requested_quantity
        executed = quantity if self.outcome is BrokerOrderOutcome.FILLED else Decimal("0")
        price = Decimal("1.1000") if executed else None
        return BrokerSubmissionResult(transmission_status=TransmissionStatus.TRANSMITTED, snapshot=BrokerOrderSnapshot("BO-1", self.outcome, quantity, executed, price, self.outcome.value, NOW), evidence=None)
    def get_order(self, broker_order_id):
        return BrokerOrderSnapshot("BO-1", self.outcome, Decimal("1000"), Decimal("1000") if self.outcome is BrokerOrderOutcome.FILLED else Decimal("0"), Decimal("1.1000") if self.outcome is BrokerOrderOutcome.FILLED else None, self.outcome.value, NOW)

def controller():
    return RuntimeDeploymentController(
        identity=DeploymentIdentity("app", "strategy", "config", "runtime"),
        mode=DeploymentMode.CONTROLLED_LIVE,
        ownership=Ownership(),
        state_port=type("State", (), {"append": lambda s, r: None, "get": lambda s, **k: None, "find_by_decision": lambda s, d: ()})(),
        audit_port=Audit(), dependency_port=Dependencies(), clock=lambda: NOW,
    )

def candidate():
    return DecisionCandidate("D-1","MS-0.6","EURUSD",Direction.BUY,ConfirmationType.CP1,"S-1",NOW,Decimal("1.1000"),Decimal("1.0950"),Decimal("1.1100"),())

def decision(): return DecisionResult("D-1", DecisionStatus.VALID, ())
def risk(): return RiskResult("D-1",Decimal(".01"),Decimal(".01"),Decimal("1000"),Decimal("1.1"),Decimal("1.095"),Decimal("1.0949"),Decimal("1.1102"),Decimal(".0051"),Decimal(".0102"),Decimal("2"),Decimal("100"),RiskStatus.RISK_AUTHORIZED,())
def governance(): return GovernanceResult("D-1",True,0,0,(),GovernanceStatus.GOVERNANCE_AUTHORIZED,())
def runtime_auth(): return ExecutionAuthorization("D-1","runtime","runtime:1",NOW)

def issue_auth():
    c = controller(); assert c.start() is RuntimeLifecycleState.RUNNING
    store, audit = Store(), Audit()
    a = LiveAuthorizationController(runtime=c, authorization_port=store, audit_port=audit, clock=lambda: NOW).issue(
        decision_id="D-1", instrument="EURUSD", runtime_authorization=runtime_auth(),
        authorized_by="operator-1", expires_at=NOW + timedelta(minutes=15))
    return c, store, a, audit

def test_live_authorization_is_scoped_and_expires():
    _, store, a, _ = issue_auth()
    assert a.status is LiveAuthorizationStatus.ACTIVE
    assert a.instrument == "EURUSD"
    assert a.runtime_context_id == "runtime:1"
    assert a.is_valid_at(NOW + timedelta(minutes=1))
    assert not a.is_valid_at(NOW + timedelta(minutes=15))

def test_live_submission_consumes_authorization_once():
    _, store, a, audit = issue_auth()
    engine = LiveExecutionEngine(authorization_port=store, broker_submission_port=Broker(), broker_read_port=Broker(), audit_port=audit, clock=lambda: NOW)
    rec = engine.submit(candidate=candidate(), decision=decision(), risk=risk(), governance=governance(), runtime_authorization=runtime_auth(), live_authorization=a, runtime_id="runtime", runtime_context_id="runtime:1")
    assert rec.state is ExecutionState.FILLED
    assert store.get(a.authorization_id).status is LiveAuthorizationStatus.CONSUMED

def test_live_authorization_cannot_be_reused():
    _, store, a, audit = issue_auth()
    broker = Broker()
    engine = LiveExecutionEngine(authorization_port=store, broker_submission_port=broker, broker_read_port=broker, audit_port=audit, clock=lambda: NOW)
    engine.submit(candidate=candidate(), decision=decision(), risk=risk(), governance=governance(), runtime_authorization=runtime_auth(), live_authorization=a, runtime_id="runtime", runtime_context_id="runtime:1")
    with pytest.raises(LiveAuthorizationConsumed):
        engine.submit(candidate=candidate(), decision=decision(), risk=risk(), governance=governance(), runtime_authorization=runtime_auth(), live_authorization=a, runtime_id="runtime", runtime_context_id="runtime:1")
    assert broker.calls == 1

def test_partial_fill_stays_submitted_until_terminal_disposition():
    _, store, a, audit = issue_auth()
    class PartialBroker(Broker):
        def submit(self, request):
            self.calls += 1
            quantity = request.requested_quantity
            return BrokerSubmissionResult(transmission_status=TransmissionStatus.TRANSMITTED, snapshot=BrokerOrderSnapshot("BO-2", BrokerOrderOutcome.PARTIALLY_FILLED, quantity, Decimal("600"), Decimal("1.1001"), "PARTIAL", NOW), evidence=None)
        def get_order(self, broker_order_id):
            return BrokerOrderSnapshot("BO-2", BrokerOrderOutcome.CANCELLED, Decimal("1000"), Decimal("600"), Decimal("1.1001"), "CANCELLED", NOW)
    broker = PartialBroker()
    engine = LiveExecutionEngine(authorization_port=store, broker_submission_port=broker, broker_read_port=broker, audit_port=audit, clock=lambda: NOW)
    rec = engine.submit(candidate=candidate(), decision=decision(), risk=risk(), governance=governance(), runtime_authorization=runtime_auth(), live_authorization=a, runtime_id="runtime", runtime_context_id="runtime:1")
    assert rec.state is ExecutionState.SUBMITTED
    assert rec.fill_classification is FillClassification.PARTIAL
    final = engine.reconcile(rec)
    assert final.state is ExecutionState.FAILED
    assert final.fill_classification is FillClassification.PARTIAL

def test_unknown_outcome_is_preserved_without_resubmission():
    _, store, a, audit = issue_auth()
    broker = Broker()
    def fail(request):
        broker.calls += 1
        raise TimeoutError("timeout")
    broker.submit = fail
    engine = LiveExecutionEngine(authorization_port=store, broker_submission_port=broker, broker_read_port=broker, audit_port=audit, clock=lambda: NOW)
    rec = engine.submit(candidate=candidate(), decision=decision(), risk=risk(), governance=governance(), runtime_authorization=runtime_auth(), live_authorization=a, runtime_id="runtime", runtime_context_id="runtime:1")
    assert rec.state is ExecutionState.SUBMITTED
    assert rec.broker_outcome is BrokerOrderOutcome.UNKNOWN
    assert rec.reconciliation_required
    assert rec.manual_reconciliation_required
    assert broker.calls == 1
    assert store.get(a.authorization_id).status is LiveAuthorizationStatus.CONSUMED
