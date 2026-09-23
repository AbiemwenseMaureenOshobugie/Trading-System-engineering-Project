"""Ports used by the MS-0.11 replay harness.

The backtester owns orchestration only. Strategy, risk, governance, decision,
execution, journal, and analytics behavior remain injected dependencies.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from trading_system.domain import (
    DecisionCandidate,
    ExitInstruction,
    ExecutionRecord,
    ExitExecutionRecord,
    PerformanceSnapshot,
    TradeJournalEntry,
    Position,
)

from .models import ReplayAccountSnapshot, ReplayDecision


class ReplayPipelinePort(Protocol):
    """Evaluate the existing ASTER pipeline using replay-scoped information."""

    def evaluate(
        self,
        *,
        cutoff: datetime,
        candles: Sequence,
        account: ReplayAccountSnapshot,
    ) -> Sequence[ReplayDecision]:
        ...


class EntryExecutionPort(Protocol):
    """Existing entry-execution boundary."""

    def submit(self, *, candidate, decision, risk, governance) -> ExecutionRecord:
        ...


class ExitInstructionPort(Protocol):
    """Existing position/exit instruction boundary."""

    def create_instruction(
        self, *, position: Position, risk, exit_type
    ) -> ExitInstruction:
        ...


class ExitExecutionPort(Protocol):
    """Existing exit-execution boundary."""

    def submit(self, *, instruction: ExitInstruction) -> ExitExecutionRecord:
        ...


class JournalFactoryPort(Protocol):
    """Create the existing journal record from completed execution evidence."""

    def create(
        self,
        *,
        entry: ExecutionRecord,
        exit: ExitExecutionRecord,
    ) -> TradeJournalEntry:
        ...


class PerformancePort(Protocol):
    """Existing downstream descriptive analytics boundary."""

    def calculate(
        self, entries: Sequence[TradeJournalEntry]
    ) -> PerformanceSnapshot:
        ...
