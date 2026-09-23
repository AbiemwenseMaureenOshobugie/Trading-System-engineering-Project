"""Application/service ports.

These Protocols describe what an application service may depend on. They do
not contain strategy rules, risk formulas, governance rules, or broker logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

from trading_system.domain import (
    TradeJournalEntry,
    AuditRecord,
    ConfirmationSequence,
    DecisionCandidate,
    DecisionRequest,
    DecisionResult,
    ExecutionRecord, ExitExecutionRecord, ExitInstruction,
    GovernanceRequest,
    GovernanceResult,
    KeyLevel,
    MarketCandle,
    MarketStructureState,
    RiskRequest,
    RiskResult,
    Timeframe,
)


@runtime_checkable
class MarketDataPort(Protocol):
    """Read canonical, validated market candles from an external market-data source."""

    def get_candles(
        self, *, symbol: str, timeframe: Timeframe, start: datetime, end: datetime
    ) -> Sequence[MarketCandle]: ...


@runtime_checkable
class H1MarketStructurePort(Protocol):
    """Evaluate H1 market structure as of an explicit completed-candle cutoff."""

    def evaluate(
        self, *, candles: Sequence[MarketCandle], evaluation_cutoff: datetime
    ) -> MarketStructureState: ...


@runtime_checkable
class KeyLevelEnginePort(Protocol):
    """Detect approved key levels from validated strategy inputs."""

    def detect(
        self, *, candles: Sequence[MarketCandle], structure: MarketStructureState
    ) -> Sequence[KeyLevel]: ...


@runtime_checkable
class ConfirmationEnginePort(Protocol):
    """Evaluate confirmation against an already-selected governing Key Level."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
        setup_key_level: KeyLevel,
    ) -> Sequence[ConfirmationSequence]: ...


@runtime_checkable
class SetupClassifierPort(Protocol):
    """Translate qualifying confirmation sequences into candidates."""

    def classify(
        self, confirmations: Sequence[ConfirmationSequence]
    ) -> Sequence[DecisionCandidate]: ...


@runtime_checkable
class RiskEnginePort(Protocol):
    """Qualify and size a strategy candidate using downstream risk inputs."""

    def assess(self, request: RiskRequest) -> RiskResult: ...


@runtime_checkable
class GovernanceEnginePort(Protocol):
    """Apply hard operational permissions to a decision candidate."""

    def authorize(self, request: GovernanceRequest) -> GovernanceResult: ...


@runtime_checkable
class DecisionEnginePort(Protocol):
    """Aggregate strategy, risk, and governance outcomes into one final state."""

    def decide(self, request: DecisionRequest) -> DecisionResult: ...


@runtime_checkable
class ExecutionPort(Protocol):
    """Submit only candidates with authorized Decision, Risk, and Governance results."""

    def submit(
        self,
        *,
        candidate: DecisionCandidate,
        decision: DecisionResult,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> ExecutionRecord: ...


@runtime_checkable
class TradeJournalPort(Protocol):
    """Append and retrieve immutable completed-trade journal entries."""

    def append(self, entry: TradeJournalEntry) -> None: ...

    def entries(self) -> tuple[TradeJournalEntry, ...]: ...


@runtime_checkable
class ExitExecutionPort(Protocol):
    """Submit an authorized exit instruction for an existing open position."""
    def submit(self, *, instruction: ExitInstruction) -> ExitExecutionRecord: ...

@runtime_checkable
class AuditPort(Protocol):
    """Record material boundary events without owning business rules."""

    def record(self, event: AuditRecord) -> None: ...


__all__ = [
    "AuditPort",
    "TradeJournalPort",
    "ConfirmationEnginePort",
    "DecisionEnginePort",
    "ExecutionPort", "ExitExecutionPort",
    "GovernanceEnginePort",
    "H1MarketStructurePort",
    "KeyLevelEnginePort",
    "MarketDataPort",
    "RiskEnginePort",
    "SetupClassifierPort",
]
