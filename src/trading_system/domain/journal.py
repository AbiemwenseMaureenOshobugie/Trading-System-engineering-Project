"""Canonical immutable trade-journal contracts for MS-0.9."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from .enums import Direction


@dataclass(frozen=True, slots=True)
class TradeJournalEntry:
    """One completed trade outcome supplied by an execution-aware journal producer.

    Entry-side fields refer to the actual entry fill. Exit-side fields refer to
    the actual exit fill. The journal does not create, infer, or modify either
    execution event.
    """

    journal_id: str
    decision_id: str
    entry_execution_id: str
    exit_execution_id: str
    strategy_version: str
    symbol: str
    direction: Direction
    executed_quantity: Decimal
    entry_execution_price: Decimal
    exit_execution_price: Decimal
    entry_execution_timestamp: datetime
    exit_execution_timestamp: datetime
    realized_pnl: Decimal

    def __post_init__(self) -> None:
        if self.executed_quantity <= 0:
            raise ValueError("executed_quantity must be positive")
        if (
            self.entry_execution_timestamp.tzinfo is None
            or self.exit_execution_timestamp.tzinfo is None
        ):
            raise ValueError("execution timestamps must be timezone-aware")
        if self.exit_execution_timestamp < self.entry_execution_timestamp:
            raise ValueError(
                "exit_execution_timestamp must not precede entry_execution_timestamp"
            )
