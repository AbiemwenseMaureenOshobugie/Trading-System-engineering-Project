"""Canonical immutable trade-journal contracts for MS-0.9."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .enums import Direction


@dataclass(frozen=True, slots=True)
class TradeJournalEntry:
    """One completed trade outcome supplied to the journal."""

    journal_id: str
    decision_id: str
    execution_id: str
    strategy_version: str
    symbol: str
    direction: Direction
    quantity: Decimal
    entry_price: Decimal
    exit_price: Decimal
    opened_at: datetime
    closed_at: datetime
    realized_pnl: Decimal

    def __post_init__(self) -> None:
        if self.quantity <= 0:
            raise ValueError("quantity must be positive")
        if self.opened_at.tzinfo is None or self.closed_at.tzinfo is None:
            raise ValueError("journal timestamps must be timezone-aware")
        if self.closed_at < self.opened_at:
            raise ValueError("closed_at must not precede opened_at")
