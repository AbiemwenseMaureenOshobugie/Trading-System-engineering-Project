"""MS-0.11 replay harness tests."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.backtest import BacktestConfig, BacktestEngine, ReplayDecision
from trading_system.domain import (
    ConfirmationType, DecisionCandidate, DecisionResult, DecisionStatus,
    Direction, GovernanceResult, GovernanceStatus, RiskResult, RiskStatus,
    ExecutionRecord, ExecutionState, PaperOrder, PaperFill, ExitType,
    ExitExecutionState, ExitExecutionRecord, ExitInstruction, ExitPaperFill,
    TradeJournalEntry, PerformanceSnapshot,
)
from trading_system.execution import ExitManager
from trading_system.session import SessionPolicyEngine


UTC = timezone.utc
T0 = datetime(2026, 9, 1, 7, 0, tzinfo=UTC)


class FakeEntryExecution:
    def submit(self, *, candidate, decision, risk, governance):
        order = PaperOrder(
            order_id=f"PO-{candidate.decision_id}",
            decision_id=candidate.decision_id,
            symbol=candidate.symbol,
            direction=candidate.direction,
            requested_entry_price=candidate.signal_entry_price,
            requested_quantity=Decimal("1"),
            submission_timestamp=candidate.signal_timestamp,
        )
        fill = PaperFill(
            fill_id=f"PF-{candidate.decision_id}",
            order_id=order.order_id,
            fill_price=order.requested_entry_price,
            executed_quantity=Decimal("1"),
            execution_timestamp=candidate.signal_timestamp,
        )
        return ExecutionRecord(
            execution_id=f"EX-{candidate.decision_id}",
            decision_id=candidate.decision_id,
            state=ExecutionState.FILLED,
            order_id=order.order_id,
            fill_id=fill.fill_id,
            order=order,
            fill=fill,
            failure_reason=None,
        )


class FakeExitExecution:
    def submit(self, *, instruction):
        fill = ExitPaperFill(
            exit_fill_id=f"XF-{instruction.exit_instruction_id}",
            exit_instruction_id=instruction.exit_instruction_id,
            actual_exit_price=instruction.trigger_price,
            executed_quantity=instruction.requested_quantity,
            exit_execution_timestamp=T0,
        )
        return ExitExecutionRecord(
            exit_execution_id=f"XE-{instruction.exit_instruction_id}",
            position_id=instruction.position_id,
            decision_id=instruction.decision_id,
            state=ExitExecutionState.FILLED,
            instruction=instruction,
            fill=fill,
            failure_reason=None,
            failure_timestamp=None,
        )


class FakeJournalFactory:
    def create(self, *, entry, exit):
        return TradeJournalEntry(
            journal_id=f"J-{entry.decision_id}",
            decision_id=entry.decision_id,
            entry_execution_id=entry.execution_id,
            exit_execution_id=exit.exit_execution_id,
            strategy_version="TEST",
            symbol=entry.order.symbol,
            direction=entry.order.direction,
            executed_quantity=exit.fill.executed_quantity,
            entry_execution_price=entry.fill.fill_price,
            exit_execution_price=exit.fill.actual_exit_price,
            entry_execution_timestamp=entry.fill.execution_timestamp,
            exit_execution_timestamp=exit.fill.exit_execution_timestamp,
            realized_pnl=Decimal("10"),
        )


class FakeAnalytics:
    def calculate(self, entries):
        return PerformanceSnapshot(
            total_trades=len(entries),
            winning_trades=len(entries),
            losing_trades=0,
            breakeven_trades=0,
            win_rate=Decimal("1"),
            gross_profit=Decimal("10") * len(entries),
            gross_loss=Decimal("0"),
            net_pnl=Decimal("10") * len(entries),
            average_trade_pnl=Decimal("10") if entries else None,
            profit_factor=None,
            max_drawdown=Decimal("0"),
            max_consecutive_losses=0,
            expectancy=Decimal("10") if entries else None,
        )


class FakePipeline:
    def __init__(self, decision):
        self.decision = decision
        self.cutoffs = []

    def evaluate(self, *, cutoff, candles, account):
        self.cutoffs.append((cutoff, tuple(c.timestamp_close for c in candles)))
        return (self.decision,) if cutoff == self.decision.candidate.signal_timestamp else ()


def make_decision(timestamp=T0):
    candidate = DecisionCandidate(
        decision_id="D-1",
        strategy_version="TEST",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id="S-1",
        signal_timestamp=timestamp,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=(),
    )
    risk = RiskResult(
        decision_id="D-1",
        requested_risk=Decimal("0.01"),
        approved_risk=Decimal("0.01"),
        position_size=Decimal("1"),
        entry_assumption=Decimal("1.1"),
        structural_stop_loss=Decimal("1.095"),
        final_stop_loss=Decimal("1.095"),
        target_price=Decimal("1.11"),
        stop_distance=Decimal("0.005"),
        target_distance=Decimal("0.01"),
        risk_reward=Decimal("2"),
        risk_amount=Decimal("100"),
        status=RiskStatus.RISK_AUTHORIZED,
        reason_codes=(),
    )
    governance = GovernanceResult("D-1", True, 0, 0, (), GovernanceStatus.GOVERNANCE_AUTHORIZED, ())
    decision = DecisionResult("D-1", DecisionStatus.VALID, ())
    return ReplayDecision(candidate, decision, risk, governance)


def config():
    return BacktestConfig(
        backtest_id="BT-1",
        strategy_versions=("TEST",),
        symbol_universe=("EURUSD",),
        timeframes=("M15",),
        historical_data_source="TEST",
        historical_data_version="1",
        start_timestamp=T0,
        end_timestamp=T0.replace(hour=9),
        initial_account_equity=Decimal("10000"),
        replay_mode="PAPER",
    )


def candle(close_time, high="1.101", low="1.099"):
    from trading_system.domain import MarketCandle, Timeframe
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        timestamp_open=close_time.replace(minute=close_time.minute-15),
        timestamp_close=close_time,
        open=Decimal("1.100"),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal("1.1005"),
    )


def test_replay_exposes_only_data_at_or_before_cutoff():
    d = make_decision()
    pipeline = FakePipeline(d)
    engine = BacktestEngine(
        pipeline=pipeline,
        entry_execution=FakeEntryExecution(),
        exit_manager=ExitManager(clock=lambda: T0),
        exit_execution=FakeExitExecution(),
        journal_factory=FakeJournalFactory(),
        analytics=FakeAnalytics(),
    )
    result = engine.run(config=config(), candles=[candle(T0), candle(T0.replace(hour=8))])
    assert result.future_data_violations == ()
    for cutoff, visible in pipeline.cutoffs:
        assert all(ts <= cutoff for ts in visible)


def test_replay_runs_existing_pipeline_and_records_entry():
    d = make_decision()
    engine = BacktestEngine(
        pipeline=FakePipeline(d),
        entry_execution=FakeEntryExecution(),
        exit_manager=ExitManager(clock=lambda: T0),
        exit_execution=FakeExitExecution(),
        journal_factory=FakeJournalFactory(),
        analytics=FakeAnalytics(),
    )
    result = engine.run(config=config(), candles=[candle(T0), candle(T0.replace(hour=8))])
    assert result.executed_entries == 1
    assert result.entry_executions[0].decision_id == "D-1"


def test_both_exit_levels_in_one_ohlc_candle_are_preserved_as_ambiguous():
    d = make_decision()
    pipeline = FakePipeline(d)
    engine = BacktestEngine(
        pipeline=pipeline,
        entry_execution=FakeEntryExecution(),
        exit_manager=ExitManager(clock=lambda: T0),
        exit_execution=FakeExitExecution(),
        journal_factory=FakeJournalFactory(),
        analytics=FakeAnalytics(),
    )
    # First candle creates the position. Second candle touches both 1.095 and 1.11.
    candles = [
        candle(T0),
        candle(T0.replace(hour=8), high="1.120", low="1.090"),
    ]
    result = engine.run(config=config(), candles=candles)
    assert result.ambiguous_executions == 1
    assert result.completed_trade_count == 0
    assert result.ambiguous_execution_events[0].startswith("AMBIGUOUS_EXIT_ORDERING:")


def test_result_is_reproducible():
    d = make_decision()
    def run():
        return BacktestEngine(
            pipeline=FakePipeline(d),
            entry_execution=FakeEntryExecution(),
            exit_manager=ExitManager(clock=lambda: T0),
            exit_execution=FakeExitExecution(),
            journal_factory=FakeJournalFactory(),
            analytics=FakeAnalytics(),
        ).run(config=config(), candles=[candle(T0)])
    assert run() == run()
