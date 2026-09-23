"""MS-0.10 exit execution contract tests."""
from datetime import datetime, timezone
from decimal import Decimal
import pytest
from trading_system.domain import Direction, ExitExecutionState, ExitType, Position, RiskResult, RiskStatus
from trading_system.execution import ExitExecutionEngine, ExitExecutionStateMachine, ExitManager, InvalidExitExecutionTransition
TS=datetime(2026,9,23,12,0,tzinfo=timezone.utc)

def pos():
    return Position("POS-001","D-001","EX-D-001","EURUSD",Direction.BUY,Decimal("1000"),Decimal("1.1000"),TS)

def risk():
    return RiskResult("D-001",Decimal(".01"),Decimal(".01"),Decimal("1000"),Decimal("1.1000"),Decimal("1.0950"),Decimal("1.0949"),Decimal("1.1102"),Decimal(".0051"),Decimal(".0102"),Decimal("2"),Decimal("100"),RiskStatus.RISK_AUTHORIZED,("RISK_AUTHORIZED",))

def test_exit_geometry():
    m=ExitManager(clock=lambda:TS)
    stop=m.create_instruction(position=pos(),risk=risk(),exit_type=ExitType.STOP_LOSS)
    target=m.create_instruction(position=pos(),risk=risk(),exit_type=ExitType.TARGET)
    assert stop.trigger_price==Decimal("1.0949")
    assert target.trigger_price==Decimal("1.1102")
    assert stop.requested_quantity==Decimal("1000")

def test_provenance_is_required():
    m=ExitManager(clock=lambda:TS)
    bad=risk()
    object.__setattr__(bad,"decision_id","D-999")
    with pytest.raises(PermissionError):
        m.create_instruction(position=pos(),risk=bad,exit_type=ExitType.TARGET)

def test_paper_exit_preserves_actual_exit_evidence():
    i=ExitManager(clock=lambda:TS).create_instruction(position=pos(),risk=risk(),exit_type=ExitType.STOP_LOSS)
    r=ExitExecutionEngine(clock=lambda:TS).submit(instruction=i)
    assert r.state is ExitExecutionState.FILLED
    assert r.fill is not None
    assert r.fill.actual_exit_price==Decimal("1.0949")
    assert r.fill.exit_execution_timestamp==TS

def test_failed_exit_has_no_fill():
    i=ExitManager(clock=lambda:TS).create_instruction(position=pos(),risk=risk(),exit_type=ExitType.TARGET)
    r=ExitExecutionEngine(clock=lambda:TS).fail(instruction=i,failure_reason="execution unavailable")
    assert r.state is ExitExecutionState.FAILED
    assert r.fill is None
    assert r.failure_reason=="execution unavailable"

@pytest.mark.parametrize(("current","target"),[
    (ExitExecutionState.CREATED,ExitExecutionState.AUTHORIZED),
    (ExitExecutionState.AUTHORIZED,ExitExecutionState.SUBMITTED),
    (ExitExecutionState.SUBMITTED,ExitExecutionState.FILLED),
    (ExitExecutionState.SUBMITTED,ExitExecutionState.FAILED),
])
def test_legal_transitions(current,target):
    assert ExitExecutionStateMachine.transition(current,target) is target

@pytest.mark.parametrize(("current","target"),[
    (ExitExecutionState.CREATED,ExitExecutionState.SUBMITTED),
    (ExitExecutionState.CREATED,ExitExecutionState.FILLED),
    (ExitExecutionState.AUTHORIZED,ExitExecutionState.FILLED),
    (ExitExecutionState.SUBMITTED,ExitExecutionState.CREATED),
    (ExitExecutionState.FILLED,ExitExecutionState.SUBMITTED),
    (ExitExecutionState.FAILED,ExitExecutionState.SUBMITTED),
])
def test_illegal_transitions(current,target):
    with pytest.raises(InvalidExitExecutionTransition):
        ExitExecutionStateMachine.transition(current,target)
