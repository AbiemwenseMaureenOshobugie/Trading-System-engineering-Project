"""Application/service ports.

These Protocols describe what an application service may depend on. They do
not contain strategy rules, risk formulas, governance rules, or broker logic.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol, Sequence

from trading_system.domain import (
    ConfirmationSequence,
    DecisionCandidate,
    ExecutionRecord,
    GovernanceResult,
    KeyLevel,
    MarketCandle,
    MarketStructureState,
    RiskResult,
    Timeframe,
)


class MarketDataPort(Protocol):
    """Read canonical, validated market candles from an external data source.

    Provider-specific raw records must be adapted, validated, and normalized
    before they cross this application boundary.
    """

    def get_candles(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Sequence[MarketCandle]: ...


class H1MarketStructurePort(Protocol):
    """Evaluate H1 market structure as of an explicit completed-candle cutoff."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        evaluation_cutoff: datetime,
    ) -> MarketStructureState: ...


class KeyLevelEnginePort(Protocol):
    """Detect approved key levels from validated strategy inputs."""

    def detect(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
    ) -> Sequence[KeyLevel]: ...


class ConfirmationEnginePort(Protocol):
    """Evaluate the approved M15 confirmation processes."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
        key_levels: Sequence[KeyLevel],
    ) -> Sequence[ConfirmationSequence]: ...


class SetupClassifierPort(Protocol):
    """Translate qualifying confirmation sequences into candidates."""

    def classify(
        self,
        confirmations: Sequence[ConfirmationSequence],
    ) -> Sequence[DecisionCandidate]: ...


class RiskEnginePort(Protocol):
    """Assess a candidate without owning strategy qualification."""

    def assess(self, candidate: DecisionCandidate) -> RiskResult: ...


class GovernanceEnginePort(Protocol):
    """Apply hard operational permissions to a decision candidate."""

    def authorize(self, candidate: DecisionCandidate) -> GovernanceResult: ...


class ExecutionPort(Protocol):
    """Submit only candidates with authorized Risk and Governance results.

    The concrete execution boundary is responsible for enforcing that both
    control results are authorized before broker submission. This port does
    not reinterpret strategy rules or modify the immutable signal definition.
    """

    def submit(
        self,
        *,
        candidate: DecisionCandidate,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> ExecutionRecord: ...


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
