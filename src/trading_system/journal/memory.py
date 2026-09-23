"""Deterministic in-memory trade journal for MS-0.9."""

from trading_system.domain import TradeJournalEntry


class InMemoryTradeJournal:
    """Append-only in-memory journal keyed by immutable journal IDs."""

    def __init__(self) -> None:
        self._entries: dict[str, TradeJournalEntry] = {}

    def append(self, entry: TradeJournalEntry) -> None:
        if entry.journal_id in self._entries:
            raise ValueError(f"duplicate journal_id: {entry.journal_id}")
        self._entries[entry.journal_id] = entry

    def entries(self) -> tuple[TradeJournalEntry, ...]:
        return tuple(
            sorted(
                self._entries.values(),
                key=lambda item: (item.exit_execution_timestamp, item.journal_id),
            )
        )

