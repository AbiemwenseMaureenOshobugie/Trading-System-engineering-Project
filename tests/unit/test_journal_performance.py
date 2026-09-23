"""Acceptance tests for MS-0.9 journal and performance analytics."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_system.analytics import PerformanceAnalytics
from trading_system.domain import Direction, PerformanceSnapshot, TradeJournalEntry
from trading_system.journal import InMemoryTradeJournal


BASE = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)


def entry(
    journal_id: str,
    pnl: str,
    *,
    offset_minutes: int = 0,
    entry_offset: int = 0,
) -> TradeJournalEntry:
    entry_time = BASE + timedelta(minutes=entry_offset)
    exit_time = BASE + timedelta(minutes=offset_minutes)
    return TradeJournalEntry(
        journal_id=journal_id,
        decision_id=f"D-{journal_id}",
        entry_execution_id=f"ENTRY-{journal_id}", exit_execution_id=f"EXIT-{journal_id}",
        strategy_version="MS-0.1.0",
        symbol="EURUSD",
        direction=Direction.BUY,
        executed_quantity=Decimal("1"),
        entry_execution_price=Decimal("1.1000"),
        exit_execution_price=Decimal("1.1010"),
        entry_execution_timestamp=entry_time,
        exit_execution_timestamp=exit_time,
        realized_pnl=Decimal(pnl),
    )


def test_ms09_t01_journal_entry_is_immutable_and_accepted() -> None:
    item = entry("J-1", "10", offset_minutes=10, entry_offset=5)
    assert item.realized_pnl == Decimal("10")
    with pytest.raises(AttributeError):
        item.realized_pnl = Decimal("20")  # type: ignore[misc]


def test_ms09_t02_naive_timestamps_are_rejected() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        TradeJournalEntry(
            journal_id="J-1",
            decision_id="D-1",
            entry_execution_id="ENTRY-1",
            exit_execution_id="EXIT-1",
            strategy_version="MS-0.1.0",
            symbol="EURUSD",
            direction=Direction.BUY,
            executed_quantity=Decimal("1"),
            entry_execution_price=Decimal("1.1"),
            exit_execution_price=Decimal("1.2"),
            entry_execution_timestamp=datetime(2026, 9, 1, 8),
            exit_execution_timestamp=BASE,
            realized_pnl=Decimal("1"),
        )


def test_ms09_t03_close_before_open_is_rejected() -> None:
    with pytest.raises(ValueError, match="exit_execution_timestamp"):
        entry("J-1", "1", offset_minutes=5, entry_offset=10)


def test_ms09_t04_non_positive_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match="executed_quantity"):
        TradeJournalEntry(
            journal_id="J-1",
            decision_id="D-1",
            entry_execution_id="ENTRY-1",
            exit_execution_id="EXIT-1",
            strategy_version="MS-0.1.0",
            symbol="EURUSD",
            direction=Direction.BUY,
            executed_quantity=Decimal("0"),
            entry_execution_price=Decimal("1.1"),
            exit_execution_price=Decimal("1.2"),
            entry_execution_timestamp=BASE,
            exit_execution_timestamp=BASE,
            realized_pnl=Decimal("1"),
        )


def test_ms09_t05_journal_stores_and_orders_entries() -> None:
    journal = InMemoryTradeJournal()
    journal.append(entry("J-2", "5", offset_minutes=20))
    journal.append(entry("J-1", "10", offset_minutes=10))
    assert tuple(item.journal_id for item in journal.entries()) == ("J-1", "J-2")


def test_ms09_t06_analytics_is_independent_of_input_order() -> None:
    items = [entry("J-2", "-5", offset_minutes=20), entry("J-1", "10", offset_minutes=10)]
    assert PerformanceAnalytics.calculate(items) == PerformanceAnalytics.calculate(list(reversed(items)))


def test_ms09_t07_win_loss_breakeven_and_win_rate() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "10", offset_minutes=10),
        entry("J-2", "-5", offset_minutes=20),
        entry("J-3", "0", offset_minutes=30),
    ])
    assert (result.winning_trades, result.losing_trades, result.breakeven_trades) == (1, 1, 1)
    assert result.win_rate == Decimal(1) / Decimal(3)


def test_ms09_t08_gross_and_net_pnl() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "10", offset_minutes=10),
        entry("J-2", "-5", offset_minutes=20),
        entry("J-3", "2", offset_minutes=30),
    ])
    assert result.gross_profit == Decimal("12")
    assert result.gross_loss == Decimal("5")
    assert result.net_pnl == Decimal("7")


def test_ms09_t09_average_and_expectancy() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "10", offset_minutes=10),
        entry("J-2", "-4", offset_minutes=20),
    ])
    assert result.average_trade_pnl == Decimal("3")
    assert result.expectancy == Decimal("3")


def test_ms09_t10_profit_factor() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "10", offset_minutes=10),
        entry("J-2", "-4", offset_minutes=20),
    ])
    assert result.profit_factor == Decimal("2.5")


def test_ms09_t11_profit_factor_is_undefined_without_gross_loss() -> None:
    result = PerformanceAnalytics.calculate([entry("J-1", "10", offset_minutes=10)])
    assert result.profit_factor is None


def test_ms09_t12_max_drawdown_starts_from_zero() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "10", offset_minutes=10),
        entry("J-2", "5", offset_minutes=20),
        entry("J-3", "-8", offset_minutes=30),
        entry("J-4", "-12", offset_minutes=40),
    ])
    assert result.max_drawdown == Decimal("20")


def test_ms09_t13_max_consecutive_losses() -> None:
    result = PerformanceAnalytics.calculate([
        entry("J-1", "-1", offset_minutes=10),
        entry("J-2", "-2", offset_minutes=20),
        entry("J-3", "3", offset_minutes=30),
        entry("J-4", "-4", offset_minutes=40),
        entry("J-5", "-5", offset_minutes=50),
        entry("J-6", "-6", offset_minutes=60),
    ])
    assert result.max_consecutive_losses == 3


def test_ms09_t14_empty_journal_has_no_fabricated_metrics() -> None:
    result = PerformanceAnalytics.calculate([])
    assert result == PerformanceSnapshot(
        total_trades=0,
        winning_trades=0,
        losing_trades=0,
        breakeven_trades=0,
        win_rate=None,
        gross_profit=Decimal("0"),
        gross_loss=Decimal("0"),
        net_pnl=Decimal("0"),
        average_trade_pnl=None,
        profit_factor=None,
        max_drawdown=Decimal("0"),
        max_consecutive_losses=0,
        expectancy=None,
    )


def test_ms09_t15_duplicate_journal_ids_are_rejected() -> None:
    journal = InMemoryTradeJournal()
    journal.append(entry("J-1", "1", offset_minutes=10))
    with pytest.raises(ValueError, match="duplicate journal_id"):
        journal.append(entry("J-1", "2", offset_minutes=20))


def test_ms09_t16_analytics_does_not_mutate_entries() -> None:
    items = [entry("J-1", "10", offset_minutes=20), entry("J-2", "-2", offset_minutes=10)]
    original = tuple(items)
    PerformanceAnalytics.calculate(items)
    assert tuple(items) == original


def test_ms09_t17_repeated_calculation_is_identical() -> None:
    items = [entry("J-1", "10", offset_minutes=10), entry("J-2", "-2", offset_minutes=20)]
    first = PerformanceAnalytics.calculate(items)
    second = PerformanceAnalytics.calculate(items)
    assert first == second


def test_ms09_t18_analytics_has_no_strategy_or_execution_authority() -> None:
    assert not hasattr(PerformanceAnalytics, "authorize")
    assert not hasattr(PerformanceAnalytics, "submit")
    assert not hasattr(PerformanceAnalytics, "decide")


def test_ms09_t19_journal_columns_are_execution_semantic_not_signal_semantic() -> None:
    item = entry("J-1", "10", offset_minutes=10, entry_offset=5)
    assert item.entry_execution_price == Decimal("1.1000")
    assert item.exit_execution_price == Decimal("1.1010")
    assert item.entry_execution_timestamp < item.exit_execution_timestamp
    assert item.entry_execution_id == "ENTRY-J-1"
    assert item.exit_execution_id == "EXIT-J-1"
