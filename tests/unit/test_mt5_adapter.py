"""MS-0.12 MT5 adapter contract tests."""

from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

import pytest

from trading_system.adapters.mt5 import MT5AdapterConfig, MT5AdapterError, MT5ConnectionState, MT5ExecutionAdapter
from trading_system.domain import ConfirmationType, DecisionCandidate, DecisionResult, DecisionStatus, Direction, GovernanceResult, GovernanceStatus, RiskResult, RiskStatus

TS=datetime(2026,9,1,10,0,tzinfo=timezone.utc)

class FakeMT5:
    ACCOUNT_TRADE_MODE_DEMO=0; TRADE_ACTION_DEAL=1; ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1; ORDER_TIME_GTC=0; ORDER_FILLING_FOK=0; SYMBOL_FILLING_FOK=1; TRADE_RETCODE_DONE=10009; TRADE_RETCODE_DONE_PARTIAL=10010
    def __init__(self,demo=True,partial=False): self.demo=demo; self.partial=partial; self.shutdown_called=False; self.requests=[]
    def initialize(self): return True
    def login(self,*args,**kwargs): return True
    def shutdown(self): self.shutdown_called=True
    def account_info(self): return SimpleNamespace(trade_mode=0 if self.demo else 2,trade_allowed=True)
    def symbol_info(self,symbol): return SimpleNamespace(visible=True,volume_min=0.01,volume_max=100.0,volume_step=0.01,filling_mode=1)
    def symbol_select(self,symbol,enable): return True
    def symbol_info_tick(self,symbol): return SimpleNamespace(ask=1.1002,bid=1.1000)
    def order_check(self,request): return SimpleNamespace(retcode=0,comment="Done")
    def order_send(self,request):
        self.requests.append(request)
        if self.partial: return SimpleNamespace(retcode=10010,order=10,deal=20,volume=request["volume"]/2,price=request["price"],comment="partial")
        return SimpleNamespace(retcode=10009,order=10,deal=20,volume=request["volume"],price=request["price"],comment="done")
    def last_error(self): return "fake-error"

class Audit:
    def record(self,event): pass

def cand(): return DecisionCandidate("D-12","MS-0.6","EURUSD",Direction.BUY,ConfirmationType.CP1,"S-12",TS,Decimal("1.1000"),Decimal("1.0950"),Decimal("1.1100"),())
def risk(): return RiskResult("D-12",Decimal("0.01"),Decimal("0.01"),Decimal("0.10"),Decimal("1.1000"),Decimal("1.0950"),Decimal("1.0949"),Decimal("1.1100"),Decimal("0.0051"),Decimal("0.0100"),Decimal("1.96"),Decimal("100"),RiskStatus.RISK_AUTHORIZED,("RISK_AUTHORIZED",))
def gov(): return GovernanceResult("D-12",True,0,0,("SESSION_ELIGIBLE",),GovernanceStatus.GOVERNANCE_AUTHORIZED,("GOVERNANCE_AUTHORIZED",))
def dec(): return DecisionResult("D-12",DecisionStatus.VALID,("RISK_AUTHORIZED","GOVERNANCE_AUTHORIZED"))
def make(fake): return MT5ExecutionAdapter(config=MT5AdapterConfig({"EURUSD":"EURUSD"}),gateway=fake,audit_port=Audit(),clock=lambda:TS)

def test_demo_guard(): 
    fake=FakeMT5(demo=False); a=make(fake)
    with pytest.raises(MT5AdapterError): a.connect()
    assert a.state is MT5ConnectionState.DISCONNECTED and fake.shutdown_called

def test_ready_demo(): 
    a=make(FakeMT5()); a.connect(); assert a.state is MT5ConnectionState.READY

def test_entry_preserves_signal_and_records_fill():
    a=make(FakeMT5()); a.connect(); r=a.submit(candidate=cand(),decision=dec(),risk=risk(),governance=gov())
    assert r.state.value=="FILLED"; assert r.order.requested_entry_price==Decimal("1.1000"); assert r.actual_fill_price==Decimal("1.1002"); assert r.broker_order_id=="10"; assert r.broker_deal_id=="20"

def test_volume_step_rejected():
    a=make(FakeMT5()); a.connect(); bad=risk(); object.__setattr__(bad,"position_size",Decimal("0.105"))
    with pytest.raises(MT5AdapterError): a.submit(candidate=cand(),decision=dec(),risk=bad,governance=gov())

def test_partial_fill_fails_closed():
    a=make(FakeMT5(partial=True)); a.connect()
    with pytest.raises(MT5AdapterError,match="partial fill"): a.submit(candidate=cand(),decision=dec(),risk=risk(),governance=gov())
