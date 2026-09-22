"""Deterministic descriptive performance analytics for MS-0.9."""

from decimal import Decimal

from trading_system.domain import PerformanceSnapshot, TradeJournalEntry


class PerformanceAnalytics:
    """Aggregate completed journal outcomes without changing system state."""

    VERSION = "MS-0.9"

    @staticmethod
    def calculate(
        entries: tuple[TradeJournalEntry, ...] | list[TradeJournalEntry],
    ) -> PerformanceSnapshot:
        ordered = tuple(sorted(entries, key=lambda item: (item.closed_at, item.journal_id)))
        total = len(ordered)

        if total == 0:
            return PerformanceSnapshot(
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

        pnls = tuple(entry.realized_pnl for entry in ordered)
        winning = sum(pnl > 0 for pnl in pnls)
        losing = sum(pnl < 0 for pnl in pnls)
        breakeven = total - winning - losing
        gross_profit = sum((pnl for pnl in pnls if pnl > 0), Decimal("0"))
        gross_loss = -sum((pnl for pnl in pnls if pnl < 0), Decimal("0"))
        net_pnl = sum(pnls, Decimal("0"))
        average = net_pnl / Decimal(total)
        profit_factor = gross_profit / gross_loss if gross_loss else None

        equity = Decimal("0")
        peak = Decimal("0")
        max_drawdown = Decimal("0")
        consecutive_losses = 0
        max_consecutive_losses = 0

        for pnl in pnls:
            equity += pnl
            if equity > peak:
                peak = equity
            drawdown = peak - equity
            if drawdown > max_drawdown:
                max_drawdown = drawdown
            if pnl < 0:
                consecutive_losses += 1
                max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)
            else:
                consecutive_losses = 0

        return PerformanceSnapshot(
            total_trades=total,
            winning_trades=winning,
            losing_trades=losing,
            breakeven_trades=breakeven,
            win_rate=Decimal(winning) / Decimal(total),
            gross_profit=gross_profit,
            gross_loss=gross_loss,
            net_pnl=net_pnl,
            average_trade_pnl=average,
            profit_factor=profit_factor,
            max_drawdown=max_drawdown,
            max_consecutive_losses=max_consecutive_losses,
            expectancy=average,
        )
