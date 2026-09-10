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
    """Read canonical market candles from an external data source."""

    def get_candles(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Sequence[MarketCandle]: ...


class H1MarketStructurePort(Protocol):
    """Evaluate H1 market structure using the authoritative methodology."""

    def evaluate(
        self,
        candles: Sequence[MarketCandle],
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


class DecisionEnginePort(Protocol):
    """Produce the final system outcome from component results.

    The exact typed decision result contract is intentionally deferred until
    the decision layer is formally specified. This port is therefore a
    dependency boundary only at MS-0.2D.
    """

    def evaluate(
        self,
        *,
        candidate: DecisionCandidate,
        risk: RiskResult,
        governance: GovernanceResult,
    ) -> str: ...


class ExecutionPort(Protocol):
    """Submit only decisions that have passed risk and governance controls."""

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
    "DecisionEnginePort",
    "ExecutionPort",
    "GovernanceEnginePort",
    "H1MarketStructurePort",
    "KeyLevelEnginePort",
    "MarketDataPort",
    "RiskEnginePort",
    "SetupClassifierPort",
]
