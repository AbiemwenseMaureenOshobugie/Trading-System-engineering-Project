"""Controlled MetaTrader 5 demo adapter for MS-0.12."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import StrEnum
from typing import Any, Mapping, Protocol

from trading_system.domain import (
    DecisionCandidate, DecisionResult, Direction, ExecutionRecord, ExecutionState,
    ExitExecutionRecord, ExitExecutionState, ExitInstruction, ExitPaperFill,
    GovernanceResult, PaperFill, PaperOrder, RiskResult,
)
from trading_system.execution.engine import ExecutionEngine


class MT5AdapterError(RuntimeError):
    """Controlled MT5 adapter failure."""


class MT5ConnectionState(StrEnum):
    UNINITIALIZED = "UNINITIALIZED"
    CONNECTED = "CONNECTED"
    READY = "READY"
    DISCONNECTED = "DISCONNECTED"


class MT5Gateway(Protocol):
    ACCOUNT_TRADE_MODE_DEMO: int
    TRADE_ACTION_DEAL: int
    ORDER_TYPE_BUY: int
    ORDER_TYPE_SELL: int
    ORDER_TIME_GTC: int
    ORDER_FILLING_FOK: int
    SYMBOL_FILLING_FOK: int
    TRADE_RETCODE_DONE: int
    TRADE_RETCODE_DONE_PARTIAL: int
    def initialize(self) -> bool: ...
    def login(self, *args: Any, **kwargs: Any) -> bool: ...
    def shutdown(self) -> None: ...
    def account_info(self) -> Any: ...
    def symbol_info(self, symbol: str) -> Any: ...
    def symbol_select(self, symbol: str, enable: bool) -> bool: ...
    def symbol_info_tick(self, symbol: str) -> Any: ...
    def order_check(self, request: Mapping[str, Any]) -> Any: ...
    def order_send(self, request: Mapping[str, Any]) -> Any: ...
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
    deviation_points: int = 20
    magic_number: int = 120012
    comment_prefix: str = "ASTER"


class MT5ExecutionAdapter:
    """Entry/exit execution adapter with a hard demo-account guard."""

    VERSION = "MS-0.12"

    def __init__(self, *, config: MT5AdapterConfig, gateway: MT5Gateway, audit_port, clock=None) -> None:
        self._config = config
        self._mt5 = gateway
        self._audit_port = audit_port
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
            kwargs = {}
            if password is not None: kwargs["password"] = password
            if server is not None: kwargs["server"] = server
            if not self._mt5.login(login, **kwargs):
                self.disconnect()
                raise MT5AdapterError(f"MT5 login failed: {self._mt5.last_error()}")
        account = self._mt5.account_info()
        if account is None:
            self.disconnect()
            raise MT5AdapterError("MT5 account information unavailable")
        if account.trade_mode != self._mt5.ACCOUNT_TRADE_MODE_DEMO:
            self.disconnect()
            raise MT5AdapterError("MS-0.12 permits demo accounts only")
        if not getattr(account, "trade_allowed", False):
            self.disconnect()
            raise MT5AdapterError("MT5 account trading is not permitted")
        self._state = MT5ConnectionState.READY

    def disconnect(self) -> None:
        self._mt5.shutdown()
        self._state = MT5ConnectionState.DISCONNECTED

    def submit(self, *, candidate: DecisionCandidate, decision: DecisionResult, risk: RiskResult, governance: GovernanceResult) -> ExecutionRecord:
        if self._state is not MT5ConnectionState.READY:
            raise MT5AdapterError("MT5 adapter is not READY")
        ExecutionEngine._assert_authorized(candidate, decision, risk, governance)
        symbol = self._resolve_symbol(candidate.symbol)
        info = self._symbol_info(symbol)
        volume = self._validate_volume(risk.position_size, info)
        self._assert_fok_supported(info)
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5AdapterError(f"MT5 tick unavailable for {symbol}")
        order_type = self._mt5.ORDER_TYPE_BUY if candidate.direction is Direction.BUY else self._mt5.ORDER_TYPE_SELL
        requested_price = Decimal(str(tick.ask if candidate.direction is Direction.BUY else tick.bid))
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "price": float(requested_price),
            "deviation": self._config.deviation_points,
            "magic": self._config.magic_number,
            "comment": f"{self._config.comment_prefix}:{candidate.decision_id}",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_FOK,
        }
        check = self._mt5.order_check(request)
        if check is None or getattr(check, "retcode", 0) != 0:
            return self._failed_record(candidate, volume, self._mt5.last_error() if check is None else getattr(check, "comment", "order_check failed"), None)
        result = self._mt5.order_send(request)
        if result is None:
            return self._failed_record(candidate, volume, self._mt5.last_error(), None)
        retcode = int(result.retcode)
        if retcode == self._mt5.TRADE_RETCODE_DONE:
            now = self._clock()
            actual_price = Decimal(str(result.price))
            actual_volume = Decimal(str(result.volume))
            order_id, deal_id = str(result.order), str(result.deal)
            requested = PaperOrder(f"MT5-{order_id}", candidate.decision_id, candidate.symbol, candidate.direction, candidate.signal_entry_price, volume, now)
            fill = PaperFill(f"MT5-{deal_id}", f"MT5-{order_id}", actual_price, actual_volume, now)
            return ExecutionRecord(
                execution_id=f"MT5-EX-{candidate.decision_id}",
                decision_id=candidate.decision_id,
                state=ExecutionState.FILLED,
                order_id=order_id,
                fill_id=deal_id,
                order=requested,
                fill=fill,
                failure_reason=None,
                broker_order_id=order_id,
                broker_deal_id=deal_id,
                broker_position_id=order_id,
                actual_fill_price=actual_price,
                actual_executed_quantity=actual_volume,
                execution_timestamp=now,
                broker_retcode=retcode,
                broker_status=getattr(result, "comment", None),
                slippage=actual_price - candidate.signal_entry_price,
            )
        if retcode == self._mt5.TRADE_RETCODE_DONE_PARTIAL:
            raise MT5AdapterError("MT5 returned a partial fill; MS-0.12 has no reconciliation semantics")
        return self._failed_record(candidate, volume, getattr(result, "comment", None) or f"MT5 retcode {retcode}", retcode)

    def submit_exit(self, *, instruction: ExitInstruction, broker_position_id: str) -> ExitExecutionRecord:
        if self._state is not MT5ConnectionState.READY:
            raise MT5AdapterError("MT5 adapter is not READY")
        symbol = self._resolve_symbol(instruction.symbol)
        info = self._symbol_info(symbol)
        volume = self._validate_volume(instruction.requested_quantity, info)
        self._assert_fok_supported(info)
        tick = self._mt5.symbol_info_tick(symbol)
        if tick is None:
            raise MT5AdapterError(f"MT5 tick unavailable for {symbol}")
        close_type = self._mt5.ORDER_TYPE_SELL if instruction.direction is Direction.BUY else self._mt5.ORDER_TYPE_BUY
        price = Decimal(str(tick.bid if instruction.direction is Direction.BUY else tick.ask))
        request = {
            "action": self._mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": close_type,
            "position": int(broker_position_id),
            "price": float(price),
            "deviation": self._config.deviation_points,
            "magic": self._config.magic_number,
            "comment": f"{self._config.comment_prefix}:EXIT:{instruction.exit_instruction_id}",
            "type_time": self._mt5.ORDER_TIME_GTC,
            "type_filling": self._mt5.ORDER_FILLING_FOK,
        }
        result = self._mt5.order_send(request)
        now = self._clock()
        if result is None:
            return ExitExecutionRecord(f"MT5-XE-{instruction.exit_instruction_id}", instruction.position_id, instruction.decision_id, ExitExecutionState.FAILED, instruction, None, str(self._mt5.last_error()), now)
        retcode = int(result.retcode)
        if retcode == self._mt5.TRADE_RETCODE_DONE:
            fill = ExitPaperFill(f"MT5-XF-{result.deal}", instruction.exit_instruction_id, Decimal(str(result.price)), Decimal(str(result.volume)), now)
            return ExitExecutionRecord(
                f"MT5-XE-{instruction.exit_instruction_id}", instruction.position_id, instruction.decision_id,
                ExitExecutionState.FILLED, instruction, fill, None, None,
                broker_order_id=str(result.order), broker_deal_id=str(result.deal),
                actual_exit_price=Decimal(str(result.price)), actual_executed_quantity=Decimal(str(result.volume)),
                exit_execution_timestamp=now, broker_retcode=retcode,
            )
        if retcode == self._mt5.TRADE_RETCODE_DONE_PARTIAL:
            raise MT5AdapterError("MT5 returned a partial exit fill; MS-0.12 has no reconciliation semantics")
        return ExitExecutionRecord(
            f"MT5-XE-{instruction.exit_instruction_id}", instruction.position_id, instruction.decision_id,
            ExitExecutionState.FAILED, instruction, None,
            getattr(result, "comment", None) or f"MT5 retcode {retcode}", now,
            broker_order_id=str(getattr(result, "order", 0)),
            broker_deal_id=str(getattr(result, "deal", 0)),
            broker_retcode=retcode,
        )

    def _resolve_symbol(self, ast_symbol: str) -> str:
        try: return self._config.symbol_map[ast_symbol]
        except KeyError as exc: raise MT5AdapterError(f"no MT5 symbol mapping configured for {ast_symbol}") from exc

    def _symbol_info(self, symbol: str):
        info = self._mt5.symbol_info(symbol)
        if info is None: raise MT5AdapterError(f"MT5 symbol unavailable: {symbol}")
        if not getattr(info, "visible", False) and not self._mt5.symbol_select(symbol, True):
            raise MT5AdapterError(f"MT5 symbol could not be selected: {symbol}")
        return info

    @staticmethod
    def _validate_volume(quantity: Decimal | None, info: Any) -> Decimal:
        if quantity is None or quantity <= 0: raise MT5AdapterError("position size must be positive")
        minimum, maximum, step = map(lambda x: Decimal(str(x)), (info.volume_min, info.volume_max, info.volume_step))
        if quantity < minimum or quantity > maximum: raise MT5AdapterError("position size violates MT5 volume limits")
        if (quantity - minimum) % step != 0: raise MT5AdapterError("position size cannot be represented by MT5 volume step")
        return quantity

    def _assert_fok_supported(self, info: Any) -> None:
        if not (int(info.filling_mode) & int(self._mt5.SYMBOL_FILLING_FOK)):
            raise MT5AdapterError("MS-0.12 requires broker-supported FOK filling")

    def _failed_record(self, candidate, volume, reason, retcode):
        now = self._clock()
        requested = PaperOrder(f"MT5-FAILED-{candidate.decision_id}", candidate.decision_id, candidate.symbol, candidate.direction, candidate.signal_entry_price, volume, now)
        return ExecutionRecord(
            execution_id=f"MT5-EX-{candidate.decision_id}", decision_id=candidate.decision_id,
            state=ExecutionState.FAILED, order_id="", fill_id=None, order=requested, fill=None,
            failure_reason=str(reason), execution_timestamp=now, broker_retcode=retcode, broker_status=str(reason),
        )
