"""MS-0.30 concrete MT5 adapter tests."""
from datetime import datetime, timezone
from decimal import Decimal
from types import SimpleNamespace
import pytest
from trading_system.adapters.mt5 import MT5AdapterConfig, MT5AdapterError, MT5BrokerAdapter, MT5ConnectionState
from trading_system.application import BrokerDiscoveryPort, BrokerPositionReadPort, BrokerReadPort, BrokerSubmissionPort
from trading_system.domain import BrokerDiscoveryOutcome, BrokerDiscoveryRequest, BrokerOrderOutcome, BrokerOrderRequest, Direction, TransmissionStatus
NOW=datetime(2026,10,8,12,0,tzinfo=timezone.utc)

class FakeMT5:
    TRADE_ACTION_DEAL=1; ORDER_TYPE_BUY=0; ORDER_TYPE_SELL=1; ORDER_TIME_GTC=0
    ORDER_FILLING_FOK=0; ORDER_FILLING_IOC=1; ORDER_FILLING_RETURN=2
    SYMBOL_FILLING_FOK=1; SYMBOL_FILLING_IOC=2
    TRADE_RETCODE_DONE=10009; TRADE_RETCODE_DONE_PARTIAL=10010; TRADE_RETCODE_PLACED=10008
    TRADE_RETCODE_REJECT=10006; TRADE_RETCODE_CANCEL=10007; TRADE_RETCODE_EXPIRED=10018
    POSITION_TYPE_BUY=0; POSITION_TYPE_SELL=1
    ORDER_STATE_PLACED=1; ORDER_STATE_PARTIAL=3; ORDER_STATE_FILLED=4; ORDER_STATE_CANCELED=5; ORDER_STATE_REJECTED=6; ORDER_STATE_EXPIRED=7
    def __init__(self): self.orders=[]; self.history_orders=[]; self.history_deals={}; self.positions=[]; self.sent=[]
    def initialize(self): return True
    def login(self,*args,**kwargs): return True
    def shutdown(self): pass
    def account_info(self): return SimpleNamespace(trade_allowed=True,trade_expert=True)
    def symbol_info(self,symbol): return SimpleNamespace(visible=True,volume_min=0.01,volume_max=100.0,volume_step=0.01,filling_mode=1)
    def symbol_select(self,symbol,enable): return True
    def symbol_info_tick(self,symbol): return SimpleNamespace(ask=1.1002,bid=1.1000)
    def order_check(self,request): return SimpleNamespace(retcode=0,comment="Done")
    def order_send(self,request):
        self.sent.append(request)
        return SimpleNamespace(retcode=10009,order=10,deal=20,volume=request["volume"],price=request["price"],comment="done")
    def orders_get(self,*args,**kwargs):
        if "ticket" in kwargs: return tuple(o for o in self.orders if o.ticket==kwargs["ticket"])
        return tuple(self.orders)
    def history_orders_get(self,*args,**kwargs):
        if "ticket" in kwargs: return tuple(o for o in self.history_orders if o.ticket==kwargs["ticket"])
        return tuple(self.history_orders)
    def history_deals_get(self,*args,**kwargs):
        if "ticket" in kwargs: return tuple(self.history_deals.get(kwargs["ticket"],()))
        return ()
    def positions_get(self,*args,**kwargs):
        if "ticket" in kwargs: return tuple(p for p in self.positions if p.ticket==kwargs["ticket"])
        if "symbol" in kwargs: return tuple(p for p in self.positions if p.symbol==kwargs["symbol"])
        return tuple(self.positions)
    def last_error(self): return "fake-error"

def make_adapter(fake=None):
    fake=fake or FakeMT5()
    adapter=MT5BrokerAdapter(config=MT5AdapterConfig({"EURUSD":"EURUSD"},FakeMT5.ORDER_FILLING_FOK),gateway=fake,clock=lambda:NOW)
    adapter.connect()
    return adapter,fake

def request():
    return BrokerOrderRequest("D-30","LEA-D-30","EURUSD",Direction.BUY,Decimal("0.10"),Decimal("1.1000"))

def test_adapter_implements_all_ms029_broker_ports():
    adapter,_=make_adapter()
    assert isinstance(adapter,BrokerSubmissionPort); assert isinstance(adapter,BrokerReadPort); assert isinstance(adapter,BrokerDiscoveryPort); assert isinstance(adapter,BrokerPositionReadPort)

def test_connection_requires_trade_permissions():
    fake=FakeMT5(); fake.account_info=lambda:SimpleNamespace(trade_allowed=False,trade_expert=True)
    adapter=MT5BrokerAdapter(config=MT5AdapterConfig({"EURUSD":"EURUSD"},FakeMT5.ORDER_FILLING_FOK),gateway=fake,clock=lambda:NOW)
    with pytest.raises(MT5AdapterError): adapter.connect()
    assert adapter.state is MT5ConnectionState.DISCONNECTED

def test_submission_uses_market_deal_and_preserves_reference_price():
    adapter,fake=make_adapter(); result=adapter.submit(request())
    assert result.transmission_status is TransmissionStatus.TRANSMITTED; assert result.snapshot is not None; assert result.snapshot.outcome is BrokerOrderOutcome.FILLED
    assert fake.sent[0]["action"]==FakeMT5.TRADE_ACTION_DEAL; assert fake.sent[0]["price"]==1.1002; assert fake.sent[0]["comment"]=="ASTER:LEA-D-30"

def test_preflight_failure_is_not_transmitted():
    adapter,fake=make_adapter(); fake.order_check=lambda request:SimpleNamespace(retcode=10014,comment="invalid volume")
    result=adapter.submit(request()); assert result.transmission_status is TransmissionStatus.NOT_TRANSMITTED; assert result.snapshot is None

def test_order_send_exception_is_unknown_not_rejected():
    adapter,fake=make_adapter(); fake.order_send=lambda request: (_ for _ in ()).throw(RuntimeError("connection lost"))
    result=adapter.submit(request()); assert result.transmission_status is TransmissionStatus.UNKNOWN; assert result.snapshot is None

def test_partial_fill_is_normalized():
    adapter,fake=make_adapter(); fake.order_send=lambda request:SimpleNamespace(retcode=10010,order=11,deal=21,volume=request["volume"]/2,price=request["price"],comment="partial")
    result=adapter.submit(request()); assert result.snapshot is not None; assert result.snapshot.outcome is BrokerOrderOutcome.PARTIALLY_FILLED

def test_discovery_rejects_ambiguity():
    adapter,fake=make_adapter(); fake.history_orders=[SimpleNamespace(ticket=10,comment="ASTER:LEA-D-30",volume_initial=0.10,volume_current=0.10,state=FakeMT5.ORDER_STATE_PLACED),SimpleNamespace(ticket=11,comment="ASTER:LEA-D-30",volume_initial=0.10,volume_current=0.10,state=FakeMT5.ORDER_STATE_PLACED)]
    result=adapter.discover(BrokerDiscoveryRequest("LEA-D-30")); assert result.outcome is BrokerDiscoveryOutcome.AMBIGUOUS_MATCH; assert result.snapshot is None

def test_position_read_is_broker_authoritative():
    adapter,fake=make_adapter(); fake.positions=[SimpleNamespace(ticket=50,symbol="EURUSD",type=FakeMT5.POSITION_TYPE_BUY,volume=0.10,price_open=1.1003)]
    result=adapter.get_position("50"); assert result is not None; assert result.broker_position_id=="50"; assert result.symbol=="EURUSD"; assert result.direction is Direction.BUY

def test_unknown_position_is_not_attributed():
    adapter,_=make_adapter(); assert adapter.get_position("999") is None
