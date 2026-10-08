"""Concrete MetaTrader 5 implementation of the MS-0.29 broker ports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping, Protocol, Sequence

from trading_system.domain import (
    BrokerDiscoveryOutcome,
    BrokerDiscoveryRequest,
    BrokerDiscoveryResult,
    BrokerEvidence,
    BrokerOrderOutcome,
    BrokerOrderRequest,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerSubmissionResult,
    Direction,
    TransmissionStatus,
)


class MT5AdapterError(RuntimeError):
    """Raised when the concrete MT5 adapter cannot satisfy its contract."""


class MT5ConnectionState(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    CONNECTED = "CONNECTED"
    READY = "READY"
    DISCONNECTED = "DISCONNECTED"


class MT5Gateway(Protocol):
    TRADE_ACTION_DEAL: int
    ORDER_TYPE_BUY: int
    ORDER_TYPE_SELL: int
    ORDER_TIME_GTC: int
    ORDER_FILLING_FOK: int
    ORDER_FILLING_IOC: int
    ORDER_FILLING_RETURN: int
    SYMBOL_FILLING_FOK: int
    SYMBOL_FILLING_IOC: int
    TRADE_RETCODE_DONE: int
    TRADE_RETCODE_DONE_PARTIAL: int
    TRADE_RETCODE_PLACED: int
    TRADE_RETCODE_REJECT: int
    TRADE_RETCODE_CANCEL: int
    TRADE_RETCODE_EXPIRED: int
    def initialize(self) -> bool: ...
    def login(self, *args: Any, **kwargs: Any) -> bool: ...
    def shutdown(self) -> None: ...
    def account_info(self) -> Any: ...
    def symbol_info(self, symbol: str) -> Any: ...
    def symbol_select(self, symbol: str, enable: bool) -> bool: ...
    def symbol_info_tick(self, symbol: str) -> Any: ...
    def order_check(self, request: Mapping[str, Any]) -> Any: ...
    def order_send(self, request: Mapping[str, Any]) -> Any: ...
    def orders_get(self, *args: Any, **kwargs: Any) -> Any: ...
    def history_orders_get(self, *args: Any, **kwargs: Any) -> Any: ...
    def history_deals_get(self, *args: Any, **kwargs: Any) -> Any: ...
    def positions_get(self, *args: Any, **kwargs: Any) -> Any: ...
    def last_error(self) -> Any: ...


class MetaTrader5Gateway:
    """Lazy wrapper around the optional MetaTrader5 package."""

    def __init__(self, mt5_module: Any | None = None) -> None:
        if mt5_module is None:
            try:
                import MetaTrader5 as mt5_module
            except ImportError as exc:
                raise MT5AdapterError(
                    "MetaTrader5 package is not installed; install the mt5 extra"
                ) from exc
        self._mt5 = mt5_module

    def __getattr__(self, name: str) -> Any:
        return getattr(self._mt5, name)


@dataclass(frozen=True, slots=True)
class MT5AdapterConfig:
    symbol_map: Mapping[str, str]
    filling_mode: int
    magic_number: int = 30030
    deviation_points: int = 20
    comment_prefix: str = "ASTER"
    discovery_lookback_hours: int = 24

    def __post_init__(self) -> None:
        if not self.symbol_map:
            raise ValueError("symbol_map must not be empty")
        if self.discovery_lookback_hours <= 0:
            raise ValueError("discovery_lookback_hours must be positive")
        if self.deviation_points < 0:
            raise ValueError("deviation_points must not be negative")


class MT5BrokerAdapter:
    """Concrete MT5 implementation of the broker-neutral MS-0.29 boundary."""

    VERSION = "MS-0.30"

    def __init__(self, *, config: MT5AdapterConfig, gateway: MT5Gateway, clock=None) -> None:
        self._config = config
        self._mt5 = gateway
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._state = MT5ConnectionState.UNINITIALIZED

    @property
    def state(self) -> MT5ConnectionState:
        return self._state

    def connect(self, *, login: int | None = None, password: str | None = None, server: str | None = None) -> None:
        if not self._mt5.initialize():
            self._state = MT5ConnectionState.DISCONNECTED
            raise MT5AdapterError(f"MT5 initialize failed: {self._mt5.last_error()}")
        self._state = MT5ConnectionState.CONNECTED
        if login is not None:
            kwargs: dict[str, Any] = {}
            if password is not None: kwargs["password"] = password
            if server is not None: kwargs["server"] = server
            if not self._mt5.login(login, **kwargs):
                self.disconnect()
                raise MT5AdapterError(f"MT5 login failed: {self._mt5.last_error()}")
        account = self._mt5.account_info()
        if account is None:
            self.disconnect()
            raise MT5AdapterError("MT5 account information unavailable")
        if not getattr(account, "trade_allowed", False):
            self.disconnect()
            raise MT5AdapterError("MT5 account trading is not permitted")
        if not getattr(account, "trade_expert", False):
            self.disconnect()
            raise MT5AdapterError("MT5 algorithmic trading is not permitted")
        self._state = MT5ConnectionState.READY

    def disconnect(self) -> None:
        self._mt5.shutdown()
        self._state = MT5ConnectionState.DISCONNECTED

    def submit(self, request: BrokerOrderRequest) -> BrokerSubmissionResult:
        self._require_ready()
        symbol = self._resolve_symbol(request.symbol)
        info = self._symbol_info(symbol)
        quantity = self._validate_quantity(request.requested_quantity, info)
        filling_mode = self._validate_filling_mode(info)
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5AdapterError(f"MT5 tick unavailable for {symbol}")
        order_type = self._mt5.ORDER_TYPE_BUY if request.direction is Direction.BUY else self._mt5.ORDER_TYPE_SELL
        price = Decimal(str(tick.ask if request.direction is Direction.BUY else tick.bid))
        native_request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(quantity),
            "type": order_type,
            "price": float(price),
            "deviation": self._config.deviation_points,
            "magic": self._config.magic_number,
            "comment": f"{self._config.comment_prefix}:{request.authorization_id}",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": filling_mode,
        }
        check = self._mt5.order_check(native_request)
        if check is None or int(getattr(check, "retcode", -1)) != 0:
            return BrokerSubmissionResult(
                TransmissionStatus.NOT_TRANSMITTED,
                None,
                None,
            )
        try:
            result = self._mt5.order_send(native_request)
        except Exception as exc:
            return BrokerSubmissionResult(
                TransmissionStatus.UNKNOWN,
                None,
                self._evidence(request, BrokerOrderOutcome.UNKNOWN, "ORDER_SEND_EXCEPTION", type(exc).__name__, (str(exc),)),
            )
        if result is None:
            return BrokerSubmissionResult(
                TransmissionStatus.UNKNOWN,
                None,
                self._evidence(request, BrokerOrderOutcome.UNKNOWN, "ORDER_SEND_NO_RESULT", str(self._mt5.last_error())),
            )
        retcode = int(getattr(result, "retcode", -1))
        outcome = self._normalize_retcode(retcode)
        broker_order_id = str(getattr(result, "order", 0) or "")
        executed_quantity = Decimal(str(getattr(result, "volume", 0) or 0))
        fill_price_raw = getattr(result, "price", None)
        fill_price = Decimal(str(fill_price_raw)) if fill_price_raw else None
        snapshot = None
        if broker_order_id:
            snapshot = BrokerOrderSnapshot(
                broker_order_id=broker_order_id,
                outcome=outcome,
                requested_quantity=quantity,
                executed_quantity=executed_quantity,
                fill_price=fill_price,
                broker_status=str(getattr(result, "comment", "")),
                observed_at=self._utc_now(),
                evidence_ref=f"MT5-{broker_order_id}",
            )
        return BrokerSubmissionResult(
            TransmissionStatus.TRANSMITTED,
            snapshot,
            self._evidence(request, outcome, str(getattr(result, "comment", "")), str(retcode), (f"broker_order_id={broker_order_id}",)),
        )

    def get_order(self, broker_order_id: str) -> BrokerOrderSnapshot:
        self._require_ready()
        ticket = int(broker_order_id)
        active = self._mt5.orders_get(ticket=ticket) or ()
        historical = self._mt5.history_orders_get(ticket=ticket) or ()
        candidates = tuple(active) + tuple(historical)
        if not candidates:
            raise MT5AdapterError(f"MT5 order not found: {broker_order_id}")
        order = candidates[-1]
        deals = self._mt5.history_deals_get(ticket=ticket) or ()
        executed_quantity = sum((Decimal(str(getattr(deal, "volume", 0) or 0)) for deal in deals), Decimal("0"))
        fill_price = self._weighted_fill_price(deals)
        outcome = self._normalize_order_state(order, executed_quantity)
        requested_quantity = Decimal(str(getattr(order, "volume_initial", None) or getattr(order, "volume_current", 0)))
        return BrokerOrderSnapshot(
            broker_order_id=str(getattr(order, "ticket", ticket)),
            outcome=outcome,
            requested_quantity=requested_quantity,
            executed_quantity=executed_quantity,
            fill_price=fill_price,
            broker_status=str(getattr(order, "state", "")),
            observed_at=self._utc_now(),
            evidence_ref=f"MT5-{ticket}",
        )

    def discover(self, request: BrokerDiscoveryRequest) -> BrokerDiscoveryResult:
        self._require_ready()
        marker = f"{self._config.comment_prefix}:{request.authorization_id}"
        now = self._utc_now()
        start = now - timedelta(hours=self._config.discovery_lookback_hours)
        active = self._mt5.orders_get() or ()
        historical = self._mt5.history_orders_get(start, now) or ()
        matches = tuple(order for order in (*active, *historical) if str(getattr(order, "comment", "")) == marker)
        if not matches:
            return BrokerDiscoveryResult(BrokerDiscoveryOutcome.NO_MATCH, None, None)
        tickets = {str(getattr(order, "ticket", "")) for order in matches}
        if len(tickets) != 1:
            return BrokerDiscoveryResult(BrokerDiscoveryOutcome.AMBIGUOUS_MATCH, None, None)
        snapshot = self.get_order(next(iter(tickets)))
        return BrokerDiscoveryResult(
            BrokerDiscoveryOutcome.UNIQUE_MATCH,
            snapshot,
            BrokerEvidence(
                evidence_ref=f"MT5-DISC-{request.authorization_id}",
                broker_name="MetaTrader5",
                adapter_name=type(self).__name__,
                adapter_version=self.VERSION,
                native_status=snapshot.broker_status,
                native_code=None,
                normalized_outcome=snapshot.outcome,
                captured_at=now,
                details=(f"authorization_id={request.authorization_id}",),
            ),
        )

    def get_position(self, broker_position_id: str) -> BrokerPositionSnapshot | None:
        self._require_ready()
        positions = self._mt5.positions_get(ticket=int(broker_position_id)) or ()
        if not positions:
            return None
        if len(positions) != 1:
            raise MT5AdapterError(f"ambiguous MT5 position identity: {broker_position_id}")
        return self._position_snapshot(positions[0])

    def list_positions(self, symbol: str) -> Sequence[BrokerPositionSnapshot]:
        self._require_ready()
        native_symbol = self._resolve_symbol(symbol)
        positions = self._mt5.positions_get(symbol=native_symbol) or ()
        return tuple(self._position_snapshot(position) for position in positions)

    def _resolve_symbol(self, symbol: str) -> str:
        try:
            return self._config.symbol_map[symbol]
        except KeyError as exc:
            raise MT5AdapterError(f"no MT5 symbol mapping configured for {symbol}") from exc

    def _symbol_info(self, symbol: str) -> Any:
        info = self._mt5.symbol_info(symbol)
        if info is None:
            raise MT5AdapterError(f"MT5 symbol unavailable: {symbol}")
        if not getattr(info, "visible", False) and not self._mt5.symbol_select(symbol, True):
            raise MT5AdapterError(f"MT5 symbol could not be selected: {symbol}")
        return info

    @staticmethod
    def _validate_quantity(quantity: Decimal, info: Any) -> Decimal:
        minimum = Decimal(str(info.volume_min))
        maximum = Decimal(str(info.volume_max))
        step = Decimal(str(info.volume_step))
        if quantity < minimum or quantity > maximum:
            raise MT5AdapterError("requested quantity violates MT5 volume limits")
        if step <= 0 or (quantity - minimum) % step != 0:
            raise MT5AdapterError("requested quantity violates MT5 volume step")
        return quantity

    def _validate_filling_mode(self, info: Any) -> int:
        allowed = int(getattr(info, "filling_mode", 0))
        mode = self._config.filling_mode
        if mode == self._mt5.ORDER_FILLING_FOK:
            flag = self._mt5.SYMBOL_FILLING_FOK
        elif mode == self._mt5.ORDER_FILLING_IOC:
            flag = self._mt5.SYMBOL_FILLING_IOC
        elif mode == self._mt5.ORDER_FILLING_RETURN:
            return mode
        else:
            raise MT5AdapterError("unsupported configured MT5 filling mode")
        if not (allowed & int(flag)):
            raise MT5AdapterError("configured MT5 filling mode is not supported")
        return mode

    def _position_snapshot(self, position: Any) -> BrokerPositionSnapshot:
        native_type = int(getattr(position, "type"))
        buy_type = int(getattr(self._mt5, "POSITION_TYPE_BUY", 0))
        direction = Direction.BUY if native_type == buy_type else Direction.SELL
        return BrokerPositionSnapshot(
            broker_position_id=str(getattr(position, "ticket")),
            symbol=self._canonical_symbol(str(getattr(position, "symbol"))),
            direction=direction,
            quantity=Decimal(str(getattr(position, "volume"))),
            average_entry_price=Decimal(str(getattr(position, "price_open"))),
            observed_at=self._utc_now(),
            evidence_ref=f"MT5-POS-{getattr(position, 'ticket')}",
        )

    def _canonical_symbol(self, native_symbol: str) -> str:
        for canonical, mapped in self._config.symbol_map.items():
            if mapped == native_symbol:
                return canonical
        return native_symbol

    def _evidence(self, request, normalized_outcome, native_status, native_code, details=()):
        return BrokerEvidence(
            evidence_ref=f"MT5-SUB-{request.authorization_id}",
            broker_name="MetaTrader5",
            adapter_name=type(self).__name__,
            adapter_version=self.VERSION,
            native_status=native_status,
            native_code=native_code,
            normalized_outcome=normalized_outcome,
            captured_at=self._utc_now(),
            details=tuple(details),
        )

    def _normalize_retcode(self, retcode: int) -> BrokerOrderOutcome:
        if retcode == self._mt5.TRADE_RETCODE_DONE: return BrokerOrderOutcome.FILLED
        if retcode == self._mt5.TRADE_RETCODE_DONE_PARTIAL: return BrokerOrderOutcome.PARTIALLY_FILLED
        if retcode == self._mt5.TRADE_RETCODE_PLACED: return BrokerOrderOutcome.PENDING
        if retcode == self._mt5.TRADE_RETCODE_REJECT: return BrokerOrderOutcome.REJECTED
        if retcode == self._mt5.TRADE_RETCODE_CANCEL: return BrokerOrderOutcome.CANCELLED
        if retcode == self._mt5.TRADE_RETCODE_EXPIRED: return BrokerOrderOutcome.EXPIRED
        return BrokerOrderOutcome.UNKNOWN

    def _normalize_order_state(self, order, executed_quantity):
        if executed_quantity > 0:
            requested = Decimal(str(getattr(order, "volume_initial", None) or getattr(order, "volume_current", executed_quantity)))
            return BrokerOrderOutcome.FILLED if executed_quantity >= requested else BrokerOrderOutcome.PARTIALLY_FILLED
        state = getattr(order, "state", None)
        mapping = {
            getattr(self._mt5, "ORDER_STATE_PLACED", object()): BrokerOrderOutcome.PENDING,
            getattr(self._mt5, "ORDER_STATE_PARTIAL", object()): BrokerOrderOutcome.PARTIALLY_FILLED,
            getattr(self._mt5, "ORDER_STATE_FILLED", object()): BrokerOrderOutcome.FILLED,
            getattr(self._mt5, "ORDER_STATE_CANCELED", object()): BrokerOrderOutcome.CANCELLED,
            getattr(self._mt5, "ORDER_STATE_REJECTED", object()): BrokerOrderOutcome.REJECTED,
            getattr(self._mt5, "ORDER_STATE_EXPIRED", object()): BrokerOrderOutcome.EXPIRED,
        }
        return mapping.get(state, BrokerOrderOutcome.UNKNOWN)

    @staticmethod
    def _weighted_fill_price(deals: Sequence[Any]) -> Decimal | None:
        total = Decimal("0")
        weighted = Decimal("0")
        for deal in deals:
            volume = Decimal(str(getattr(deal, "volume", 0) or 0))
            price = Decimal(str(getattr(deal, "price", 0) or 0))
            total += volume
            weighted += volume * price
        return weighted / total if total > 0 else None

    def _require_ready(self) -> None:
        if self._state is not MT5ConnectionState.READY:
            raise MT5AdapterError("MT5 adapter is not READY")

    def _utc_now(self) -> datetime:
        value = self._clock()
        if value.tzinfo is None:
            raise ValueError("adapter clock must return a timezone-aware datetime")
        return value.astimezone(timezone.utc)


# Backward import compatibility for the old class name.
MT5ExecutionAdapter = MT5BrokerAdapter
