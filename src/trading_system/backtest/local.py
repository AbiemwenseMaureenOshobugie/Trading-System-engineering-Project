"""Local historical-data loading and real-component replay composition.

All non-market assumptions are explicit inputs. This module does not add
strategy, risk, governance, session, or execution rules.
"""
from __future__ import annotations

import csv
from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from typing import Mapping, Sequence

from trading_system.analytics import PerformanceAnalytics
from trading_system.backtest.engine import BacktestEngine
from trading_system.backtest.models import ReplayAccountSnapshot, ReplayDecision
from trading_system.decision import DecisionEngine
from trading_system.domain import (
    AuditRecord, DecisionRequest, DecisionStatus, Direction, GovernanceRequest,
    KeyLevel, MarketCandle, RiskRequest, RiskStatus, Timeframe,
)
from trading_system.execution import ExecutionEngine, ExitExecutionEngine, ExitManager
from trading_system.governance import GovernanceEngine
from trading_system.journal import InMemoryTradeJournal
from trading_system.risk import RiskEngine
from trading_system.session import SessionPolicyEngine
from trading_system.strategy.classification import SetupClassifier
from trading_system.strategy.confirmation import M15ConfirmationEngine
from trading_system.strategy.governing_key_level import GoverningKeyLevelEngine
from trading_system.strategy.key_levels import KeyLevelDetectionEngine
from trading_system.strategy.market_structure import H1MarketStructureEngine


class HistoricalCSVError(ValueError):
    """CSV history cannot safely be used for replay."""


class HistoricalCSVAdapter:
    """Load completed, validated OHLC candles from an explicit CSV file."""

    REQUIRED = {"timestamp_open", "timestamp_close", "open", "high", "low", "close"}

    @classmethod
    def load(cls, *, path: str | Path, symbol: str, timeframe: Timeframe,
             start: datetime, end: datetime) -> tuple[MarketCandle, ...]:
        if start.tzinfo is None or end.tzinfo is None or start >= end:
            raise ValueError("start/end must be timezone-aware and start < end")
        file = Path(path)
        if not file.is_file():
            raise FileNotFoundError(file)
        source = f"csv:{file.resolve()}:{sha256(file.read_bytes()).hexdigest()}"
        output: list[MarketCandle] = []
        seen: set[datetime] = set()
        with file.open("r", newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            missing = cls.REQUIRED - set(reader.fieldnames or ())
            if missing:
                raise HistoricalCSVError(f"missing columns: {sorted(missing)}")
            for line, row in enumerate(reader, 2):
                try:
                    row_symbol = (row.get("symbol") or symbol).strip().upper()
                    row_timeframe = (row.get("timeframe") or timeframe.value).strip().upper()
                    if row_symbol != symbol.upper() or row_timeframe != timeframe.value:
                        raise HistoricalCSVError(f"line {line}: symbol/timeframe mismatch")
                    opened = _utc(row["timestamp_open"])
                    closed = _utc(row["timestamp_close"])
                    numbers = {key: Decimal(row[key].strip()) for key in ("open", "high", "low", "close")}
                    volume_text = (row.get("volume") or "").strip()
                    volume = Decimal(volume_text) if volume_text else None
                    candle = MarketCandle(
                        symbol=symbol.upper(), timeframe=timeframe,
                        timestamp_open=opened, timestamp_close=closed,
                        open=numbers["open"], high=numbers["high"], low=numbers["low"],
                        close=numbers["close"], volume=volume, source=source,
                    )
                except HistoricalCSVError:
                    raise
                except (KeyError, ValueError, InvalidOperation) as exc:
                    raise HistoricalCSVError(f"line {line}: invalid candle: {exc}") from exc
                if candle.timestamp_open in seen:
                    raise HistoricalCSVError(f"line {line}: duplicate candle open timestamp")
                seen.add(candle.timestamp_open)
                if start <= candle.timestamp_close <= end:
                    output.append(candle)
        output.sort(key=lambda c: (c.timestamp_close, c.timestamp_open))
        if not output:
            raise HistoricalCSVError("no candles in the requested interval")
        return tuple(output)


class ReplayQualificationInputs:
    """Explicit execution-cost and instrument inputs for historical qualification."""

    def __init__(self, *, value_per_price_unit: Mapping[str, Decimal],
                 spread: Decimal, slippage: Decimal, noise: Decimal,
                 volatility_adjustment: Decimal) -> None:
        self.value_per_price_unit = dict(value_per_price_unit)
        self.spread, self.slippage = spread, slippage
        self.noise, self.volatility_adjustment = noise, volatility_adjustment
        for name, value in (("spread", spread), ("slippage", slippage),
                            ("noise", noise), ("volatility_adjustment", volatility_adjustment)):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if not self.value_per_price_unit or any(v <= 0 for v in self.value_per_price_unit.values()):
            raise ValueError("positive value_per_price_unit must be supplied for every symbol")


class _ReplayClock:
    def __init__(self) -> None:
        self.value = datetime(1970, 1, 1, tzinfo=timezone.utc)

    def set(self, value: datetime) -> None:
        if value.tzinfo is None:
            raise ValueError("replay cutoff must be timezone-aware")
        self.value = value.astimezone(timezone.utc)

    def __call__(self) -> datetime:
        return self.value


class RealReplayPipeline:
    """Invoke ASTER's real strategy, risk, governance, and decision components."""

    def __init__(self, *, qualification: ReplayQualificationInputs, replay_clock: _ReplayClock) -> None:
        self.qualification = qualification
        self.clock = replay_clock
        self.structure = H1MarketStructureEngine()
        self.key_levels = KeyLevelDetectionEngine()
        self.selector = GoverningKeyLevelEngine()
        self.confirmation = M15ConfirmationEngine()
        self.classifier = SetupClassifier()
        self.risk = RiskEngine()
        self.governance = GovernanceEngine()
        self.decision = DecisionEngine()
        self.session = SessionPolicyEngine()
        self.trace: list[dict] = []

    def evaluate(self, *, cutoff: datetime, candles: Sequence[MarketCandle],
                 account: ReplayAccountSnapshot) -> Sequence[ReplayDecision]:
        self.clock.set(cutoff)
        visible = tuple(c for c in candles if c.timestamp_close <= cutoff)
        h1 = tuple(c for c in visible if c.timeframe is Timeframe.H1)
        m15 = tuple(c for c in visible if c.timeframe is Timeframe.M15)
        if not h1 or not m15:
            return ()
        structure = self.structure.evaluate(candles=h1, evaluation_cutoff=cutoff)
        levels = tuple(self.key_levels.detect(candles=h1, structure=structure))
        direction = (Direction.BUY if structure.regime.value == "UPTREND"
                     else Direction.SELL if structure.regime.value == "DOWNTREND" else None)
        if direction is None:
            return ()
        selected = self.selector.select(key_levels=levels, structure=structure, direction=direction)
        if selected.selected_key_level is None:
            return ()
        confirmations = tuple(self.confirmation.evaluate(
            candles=tuple((*h1, *m15)), structure=structure,
            setup_key_level=selected.selected_key_level,
        ))
        candidates = self.classifier.classify(confirmations)
        candles_by_ref = {c.timestamp_open.isoformat(): c for c in visible}
        results: list[ReplayDecision] = []
        for original in candidates:
            if original.signal_timestamp > cutoff:
                continue
            confirmation = next((x for x in confirmations if x.setup_id == original.setup_id), None)
            if confirmation is None:
                continue
            referenced = [candles_by_ref.get(ref) for ref in confirmation.candle_refs]
            referenced = [c for c in referenced if c is not None]
            if not referenced:
                continue
            # CP-1 structural stop uses its rejection candle; CP-2 uses C1,
            # or the frozen sweep extreme when the confirmation identified one.
            if original.setup_type.value == "CP-1":
                structural_candle = referenced[1] if len(referenced) >= 2 else referenced[0]
                stop = structural_candle.low if direction is Direction.BUY else structural_candle.high
            else:
                stop = confirmation.controlling_extreme
                if stop is None:
                    stop = referenced[0].low if direction is Direction.BUY else referenced[0].high
            candidate = replace(original, proposed_stop_loss=stop)
            unit_value = self.qualification.value_per_price_unit.get(candidate.symbol)
            setup_refs = [ref.removeprefix("key_level:") for ref in candidate.evidence_refs if ref.startswith("key_level:")]
            if unit_value is None or len(setup_refs) != 1 or not any(k.active and k.key_level_id == setup_refs[0] for k in levels):
                decision = self.decision.decide(DecisionRequest(candidate, False, None, None))
                self.trace.append({"cutoff": cutoff, "candidate": candidate, "decision": decision,
                                   "reason": "QUALIFICATION_CONTEXT_UNAVAILABLE"})
                continue
            risk_request = RiskRequest(
                candidate=candidate, active_key_levels=levels, setup_key_level_id=setup_refs[0],
                account_equity=account.account_equity, spread=self.qualification.spread,
                slippage=self.qualification.slippage, noise=self.qualification.noise,
                volatility_adjustment=self.qualification.volatility_adjustment,
                value_per_price_unit=unit_value,
            )
            risk = self.risk.assess(risk_request)
            governance = None
            if risk.status is RiskStatus.RISK_AUTHORIZED:
                session = self.session.evaluate(cutoff.astimezone(timezone.utc))
                governance = self.governance.authorize(GovernanceRequest(
                    candidate=candidate, instrument_session_eligible=session.is_trading_permitted,
                    daily_trade_count=account.daily_trade_count, daily_loss_count=account.daily_loss_count,
                ))
            decision = self.decision.decide(DecisionRequest(candidate, False, risk, governance))
            self.trace.append({"cutoff": cutoff, "candidate": candidate, "risk": risk,
                               "governance": governance, "decision": decision})
            if risk.status is RiskStatus.RISK_AUTHORIZED and governance is not None:
                results.append(ReplayDecision(candidate, decision, risk, governance))
        return tuple(results)


class ExecutionJournalFactory:
    """Create journal entries from the existing entry/exit execution records."""

    def __init__(self, *, value_per_price_unit: Mapping[str, Decimal]) -> None:
        self.values = dict(value_per_price_unit)

    def create(self, *, entry, exit):
        from trading_system.domain import TradeJournalEntry
        if entry.fill is None or exit.fill is None:
            raise ValueError("journal requires both entry and exit fills")
        value = self.values.get(entry.order.symbol)
        if value is None:
            raise ValueError(f"missing contract value for {entry.order.symbol}")
        sign = Decimal("1") if entry.order.direction is Direction.BUY else Decimal("-1")
        pnl = ((exit.fill.actual_exit_price - entry.fill.fill_price) * sign
               * entry.fill.executed_quantity * value)
        return TradeJournalEntry(
            journal_id=f"J-{entry.decision_id}-{exit.exit_execution_id}",
            decision_id=entry.decision_id, entry_execution_id=entry.execution_id,
            exit_execution_id=exit.exit_execution_id, strategy_version="MS-0.22",
            symbol=entry.order.symbol, direction=entry.order.direction,
            executed_quantity=entry.fill.executed_quantity,
            entry_execution_price=entry.fill.fill_price,
            exit_execution_price=exit.fill.actual_exit_price,
            entry_execution_timestamp=entry.fill.execution_timestamp,
            exit_execution_timestamp=exit.fill.exit_execution_timestamp, realized_pnl=pnl,
        )


class _AuditSink:
    def __init__(self) -> None:
        self.records: list[AuditRecord] = []

    def record(self, event: AuditRecord) -> None:
        self.records.append(event)


def compose_replay_pipeline(*, qualification: ReplayQualificationInputs,
                            replay_clock: _ReplayClock | None = None) -> RealReplayPipeline:
    """Compose the existing deterministic ASTER strategy pipeline."""
    return RealReplayPipeline(qualification=qualification, replay_clock=replay_clock or _ReplayClock())


def compose_backtest_engine(*, qualification: ReplayQualificationInputs) -> tuple[BacktestEngine, RealReplayPipeline]:
    """Compose the existing replay harness and paper execution dependencies."""
    clock = _ReplayClock()
    audit = _AuditSink()
    pipeline = compose_replay_pipeline(qualification=qualification, replay_clock=clock)
    engine = BacktestEngine(
        pipeline=pipeline, entry_execution=ExecutionEngine(audit_port=audit, clock=clock),
        exit_manager=ExitManager(clock=clock), exit_execution=ExitExecutionEngine(clock=clock),
        journal_factory=ExecutionJournalFactory(value_per_price_unit=qualification.value_per_price_unit),
        analytics=PerformanceAnalytics(),
    )
    return engine, pipeline


def _utc(value: str) -> datetime:
    result = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timestamp must include a timezone")
    return result.astimezone(timezone.utc)
