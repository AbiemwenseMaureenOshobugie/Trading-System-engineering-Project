"""Canonical immutable performance analytics result for MS-0.9."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass(frozen=True, slots=True)
class PerformanceSnapshot:
    """Descriptive performance metrics over completed journal entries."""

    total_trades: int
    winning_trades: int
    losing_trades: int
    breakeven_trades: int
    win_rate: Optional[Decimal]
    gross_profit: Decimal
    gross_loss: Decimal
    net_pnl: Decimal
    average_trade_pnl: Optional[Decimal]
    profit_factor: Optional[Decimal]
    max_drawdown: Decimal
    max_consecutive_losses: int
    expectancy: Optional[Decimal]
