"""Application/service ports.

These Protocols describe what an application service may depend on. They do
not contain strategy rules, risk formulas, governance rules, or broker logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence, runtime_checkable

from trading_system.domain import (
    ConfirmationSequence,
    DecisionCandidate,
    ExecutionRecord,
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

    def authorize(self, candidate: DecisionCandidate) -> GovernanceResult: ...


@runtime_checkable
class ExecutionPort(Protocol):
    """Submit only candidates with authorized Risk and Governance results."""

    def submit(
        self,
        *,
        candidate: DecisionCandidate,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> ExecutionRecord: ...


@runtime_checkable
class AuditPort(Protocol):
    """Record material boundary events without owning business rules."""

    def record(self, event: object) -> None: ...


__all__ = [
    "AuditPort",
    "ConfirmationEnginePort",
    "ExecutionPort",
    "GovernanceEnginePort",
    "H1MarketStructurePort",
    "KeyLevelEnginePort",
    "MarketDataPort",
    "RiskEnginePort",
    "SetupClassifierPort",
]
