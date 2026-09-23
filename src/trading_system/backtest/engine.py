"""Deterministic MS-0.11 historical replay orchestrator."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal
from typing import Callable, Sequence

from trading_system.domain import (
    Direction,
    ExecutionRecord,
    ExitExecutionRecord,
    ExitType,
    PerformanceSnapshot,
    Position,
    TradeJournalEntry,
)

from .models import BacktestConfig, BacktestResult, ReplayAccountSnapshot, ReplayDecision


@dataclass(frozen=True, slots=True)
class _ActivePosition:
    position: Position
    entry: ExecutionRecord
    risk: object
    stop_instruction: object
    target_instruction: object
    ambiguous: bool = False


class BacktestEngine:
    """Thin sequential replay harness around the existing ASTER pipeline."""

    VERSION = "MS-0.11"

    def __init__(
        self,
        *,
        pipeline,
        entry_execution,
        exit_manager,
        exit_execution,
        journal_factory,
        analytics,
    ) -> None:
        self._pipeline = pipeline
        self._entry_execution = entry_execution
        self._exit_manager = exit_manager
        self._exit_execution = exit_execution
        self._journal_factory = journal_factory
        self._analytics = analytics

    def run(
        self,
        *,
        config: BacktestConfig,
        candles: Sequence,
    ) -> BacktestResult:
        ordered = self._validate_history(config, candles)
        cutoffs = tuple(sorted({c.timestamp_close for c in ordered}))

        active: dict[str, _ActivePosition] = {}
        entries: list[ExecutionRecord] = []
        exits: list[ExitExecutionRecord] = []
        completed_positions: list[Position] = []
        completed_trades: list[TradeJournalEntry] = []
        failed: list[object] = []
        ambiguous: list[str] = []
        future_violations: list[str] = []
        ordering_violations: list[str] = []
        seen_decisions: set[str] = set()
        daily_trade_count = 0
        daily_loss_count = 0

        for cutoff in cutoffs:
            visible = tuple(
                candle for candle in ordered
                if candle.timestamp_close <= cutoff
            )

            account = self._snapshot(
                config,
                cutoff,
                active,
                completed_trades,
                daily_trade_count,
                daily_loss_count,
            )

            decisions = tuple(
                self._pipeline.evaluate(
                    cutoff=cutoff,
                    candles=visible,
                    account=account,
                )
            )

            for item in decisions:
                self._check_decision_cutoff(item, cutoff, future_violations)
                if item.candidate.decision_id in seen_decisions:
                    continue
                seen_decisions.add(item.candidate.decision_id)

                if item.decision.status.value == "WAIT":
                    continue
                if item.decision.status.value == "RISK_REJECTED":
                    continue
                if item.decision.status.value == "GOVERNANCE_BLOCKED":
                    continue
                if item.decision.status.value != "VALID":
                    continue

                execution = self._entry_execution.submit(
                    candidate=item.candidate,
                    decision=item.decision,
                    risk=item.risk,
                    governance=item.governance,
                )
                entries.append(execution)

                if execution.fill is None:
                    failed.append(execution)
                    continue

                position = Position(
                    position_id=f"POS-{execution.execution_id}",
                    decision_id=execution.decision_id,
                    entry_execution_id=execution.execution_id,
                    symbol=execution.order.symbol,
                    direction=execution.order.direction,
                    open_quantity=execution.fill.executed_quantity,
                    entry_execution_price=execution.fill.fill_price,
                    entry_execution_timestamp=execution.fill.execution_timestamp,
                )
                stop = self._exit_manager.create_instruction(
                    position=position,
                    risk=item.risk,
                    exit_type=ExitType.STOP_LOSS,
                )
                target = self._exit_manager.create_instruction(
                    position=position,
                    risk=item.risk,
                    exit_type=ExitType.TARGET,
                )
                active[position.position_id] = _ActivePosition(
                    position=position,
                    entry=execution,
                    risk=item.risk,
                    stop_instruction=stop,
                    target_instruction=target,
                )
                daily_trade_count += 1

            # Existing positions are evaluated against the historical evidence
            # available at this replay point. The resolver deliberately refuses
            # to invent ordering when both exits are touched in one OHLC candle.
            for position_id, state in tuple(active.items()):
                if state.ambiguous:
                    continue
                candle = self._position_candle(state.position, visible, cutoff)
                if candle is None:
                    continue
                stop_hit = self._touches_exit(candle, state.stop_instruction.trigger_price)
                target_hit = self._touches_exit(candle, state.target_instruction.trigger_price)
                if not stop_hit and not target_hit:
                    continue
                if stop_hit and target_hit:
                    ambiguous.append(
                        f"AMBIGUOUS_EXIT_ORDERING:{position_id}:{candle.timestamp_close.isoformat()}"
                    )
                    active[position_id] = replace(state, ambiguous=True)
                    continue

                instruction = (
                    state.stop_instruction if stop_hit else state.target_instruction
                )
                exit_record = self._exit_execution.submit(instruction=instruction)
                exits.append(exit_record)

                if exit_record.fill is None:
                    failed.append(exit_record)
                    continue

                try:
                    journal = self._journal_factory.create(
                        entry=state.entry,
                        exit=exit_record,
                    )
                except Exception as exc:
                    ordering_violations.append(
                        f"JOURNAL_CREATION_FAILED:{position_id}:{type(exc).__name__}"
                    )
                    continue

                completed_trades.append(journal)
                completed_positions.append(state.position)
                del active[position_id]
                if journal.realized_pnl < 0:
                    daily_loss_count += 1

        performance = (
            self._analytics.calculate(tuple(completed_trades))
            if completed_trades
            else None
        )
        realized = sum(
            (entry.realized_pnl for entry in completed_trades),
            Decimal("0"),
        )
        final_equity = config.initial_account_equity + realized

        valid = len(entries)
        return BacktestResult(
            backtest_id=config.backtest_id,
            backtest_version=self.VERSION,
            strategy_versions=config.strategy_versions,
            start_timestamp=config.start_timestamp,
            end_timestamp=config.end_timestamp,
            symbol_universe=config.symbol_universe,
            timeframes=config.timeframes,
            historical_data_source=config.historical_data_source,
            historical_data_version=config.historical_data_version,
            initial_account_equity=config.initial_account_equity,
            final_account_equity=final_equity,
            replay_mode=config.replay_mode,
            entry_executions=tuple(entries),
            exit_executions=tuple(exits),
            completed_positions=tuple(completed_positions),
            completed_trades=tuple(completed_trades),
            failed_executions=tuple(failed),
            ambiguous_execution_events=tuple(ambiguous),
            performance=performance,
            strategy_candidates=len(seen_decisions),
            valid_decisions=valid,
            wait_decisions=0,
            risk_rejections=0,
            governance_blocks=0,
            executed_entries=len(entries),
            completed_trade_count=len(completed_trades),
            ambiguous_executions=len(ambiguous),
            future_data_violations=tuple(future_violations),
            ordering_violations=tuple(ordering_violations),
        )

    @staticmethod
    def _validate_history(config: BacktestConfig, candles: Sequence) -> tuple:
        ordered = tuple(sorted(candles, key=lambda c: (c.timestamp_close, c.timestamp_open)))
        for left, right in zip(ordered, ordered[1:]):
            if right.timestamp_close < left.timestamp_close:
                raise ValueError("historical candles must be chronological")
        return tuple(
            candle for candle in ordered
            if config.start_timestamp <= candle.timestamp_close <= config.end_timestamp
            and candle.symbol in config.symbol_universe
        )

    @staticmethod
    def _snapshot(
        config,
        cutoff,
        active,
        completed,
        daily_trades,
        daily_losses,
    ) -> ReplayAccountSnapshot:
        realized = sum((item.realized_pnl for item in completed), Decimal("0"))
        positions = tuple(state.position for state in active.values())
        return ReplayAccountSnapshot(
            account_equity=config.initial_account_equity + realized,
            realized_pnl=realized,
            open_positions=positions,
            completed_trades=tuple(completed),
            daily_trade_count=daily_trades,
            daily_loss_count=daily_losses,
            replay_timestamp=cutoff,
        )

    @staticmethod
    def _check_decision_cutoff(item: ReplayDecision, cutoff, violations) -> None:
        if item.candidate.signal_timestamp > cutoff:
            violations.append(
                f"FUTURE_SIGNAL:{item.candidate.decision_id}:{item.candidate.signal_timestamp.isoformat()}"
            )

    @staticmethod
    def _position_candle(position: Position, visible: Sequence, cutoff):
        candidates = [
            c for c in visible
            if c.symbol == position.symbol and c.timestamp_close == cutoff
            and c.timestamp_close > position.entry_execution_timestamp
        ]
        return candidates[0] if candidates else None

    @staticmethod
    def _touches_exit(candle, trigger: Decimal) -> bool:
        return candle.low <= trigger <= candle.high


__all__ = ["BacktestEngine"]
