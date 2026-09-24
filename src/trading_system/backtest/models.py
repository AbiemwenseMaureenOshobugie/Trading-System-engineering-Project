"""Canonical MS-0.11 replay contracts and immutable result models."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from trading_system.domain import (
    DecisionCandidate,
    DecisionResult,
    ExecutionRecord,
    ExitExecutionRecord,
    KeyLevel,
    PerformanceSnapshot,
    Position,
    RiskResult,
    GovernanceResult,
    TradeJournalEntry,
)


@dataclass(frozen=True, slots=True)
class BacktestConfig:
    """Immutable configuration identifying one deterministic replay."""

    backtest_id: str
    strategy_versions: tuple[str, ...]
    symbol_universe: tuple[str, ...]
    timeframes: tuple[str, ...]
    historical_data_source: str
    historical_data_version: str
    start_timestamp: datetime
    end_timestamp: datetime
    initial_account_equity: Decimal
    replay_mode: str

    def __post_init__(self) -> None:
        if self.start_timestamp.tzinfo is None or self.end_timestamp.tzinfo is None:
            raise ValueError("backtest timestamps must be timezone-aware")
        if self.start_timestamp >= self.end_timestamp:
            raise ValueError("start_timestamp must precede end_timestamp")
        if self.initial_account_equity <= 0:
            raise ValueError("initial_account_equity must be positive")


@dataclass(frozen=True, slots=True)
class ReplayDecision:
    """One already-evaluated ASTER decision at a historical cutoff."""

    candidate: DecisionCandidate
    decision: DecisionResult
    risk: RiskResult
    governance: GovernanceResult


@dataclass(frozen=True, slots=True)
class ReplayAccountSnapshot:
    """Replay state exposed to the existing ASTER pipeline."""

    account_equity: Decimal
    realized_pnl: Decimal
    open_positions: tuple[Position, ...]
    completed_trades: tuple[TradeJournalEntry, ...]
    daily_trade_count: int
    daily_loss_count: int
    replay_timestamp: datetime


@dataclass(frozen=True, slots=True)
class BacktestResult:
    """Deterministic, auditable result of one historical replay."""

    backtest_id: str
    backtest_version: str
    strategy_versions: tuple[str, ...]
    start_timestamp: datetime
    end_timestamp: datetime
    symbol_universe: tuple[str, ...]
    timeframes: tuple[str, ...]
    historical_data_source: str
    historical_data_version: str
    initial_account_equity: Decimal
    final_account_equity: Decimal
    replay_mode: str
    entry_executions: tuple[ExecutionRecord, ...]
    exit_executions: tuple[ExitExecutionRecord, ...]
    completed_positions: tuple[Position, ...]
    completed_trades: tuple[TradeJournalEntry, ...]
    failed_executions: tuple[object, ...]
    ambiguous_execution_events: tuple[str, ...]
    performance: Optional[PerformanceSnapshot]
    strategy_candidates: int
    valid_decisions: int
    wait_decisions: int
    risk_rejections: int
    governance_blocks: int
    executed_entries: int
    completed_trade_count: int
    ambiguous_executions: int
    future_data_violations: tuple[str, ...]
    ordering_violations: tuple[str, ...]
