"""Application/service ports.

These Protocols describe what an application service may depend on. They do
not contain strategy rules, risk formulas, governance rules, or broker logic.
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Protocol, Sequence, runtime_checkable

if TYPE_CHECKING:
    from trading_system.domain import ObservationIdentity, ObservationResult, ObservationRevision

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
    GoverningKeyLevelRequest,
    GoverningKeyLevelResult,
    KeyLevel,
    MarketCandle,
    MarketStructureState,
    RiskRequest,
    RiskResult,
    Timeframe,
)
from trading_system.domain.qualification import QualificationContextResult


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
class GoverningKeyLevelPort(Protocol):
    """Select the single governing Key Level for an H1 thesis."""

    def select(self, request: GoverningKeyLevelRequest) -> GoverningKeyLevelResult: ...


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
class AccountStatePort(Protocol):
    """Supply authoritative account equity at qualification time."""

    def get_account_equity(self, *, at: datetime) -> Decimal: ...


@runtime_checkable
class MarketExecutionContextPort(Protocol):
    """Supply authoritative current market execution context."""

    def get_spread(self, *, symbol: str, at: datetime) -> Decimal: ...


@runtime_checkable
class ExecutionHistoryPort(Protocol):
    """Supply authoritative completed-trade execution history facts."""

    def get_slippage(self, *, symbol: str, at: datetime) -> Decimal: ...

    def get_daily_trade_count(self, *, symbol: str, at: datetime) -> int: ...

    def get_daily_loss_count(self, *, symbol: str, at: datetime) -> int: ...


@runtime_checkable
class NoisePolicyPort(Protocol):
    """Supply the authoritative directional H1 noise value."""

    def get_noise(
        self, *, candidate: DecisionCandidate, structure: MarketStructureState, at: datetime
    ) -> Decimal: ...


@runtime_checkable
class VolatilityPolicyPort(Protocol):
    """Supply the authoritative volatility adjustment."""

    def get_volatility_adjustment(
        self, *, candidate: DecisionCandidate, at: datetime
    ) -> Decimal: ...


@runtime_checkable
class InstrumentSpecificationPort(Protocol):
    """Supply authoritative account-currency value per price unit."""

    def get_value_per_price_unit(self, *, symbol: str, at: datetime) -> Decimal: ...


@runtime_checkable
class ObservationQualificationContextPort(Protocol):
    """Assemble authoritative Risk/Governance requests at qualification time."""

    def qualify(
        self,
        *,
        candidate: DecisionCandidate,
        key_levels: Sequence[KeyLevel],
        structure: MarketStructureState,
        boundary: datetime,
        qualification_timestamp: datetime,
    ) -> QualificationContextResult: ...


@runtime_checkable
class TradeJournalPort(Protocol):
    """Append and retrieve immutable completed-trade journal entries."""

    def append(self, entry: TradeJournalEntry) -> None: ...

    def entries(self) -> tuple[TradeJournalEntry, ...]: ...


@runtime_checkable
class ExitExecutionPort(Protocol):
    """Submit an authorized exit instruction for an existing open position."""

    def submit(self, *, instruction: ExitInstruction, broker_position_id: str) -> ExitExecutionRecord: ...


@runtime_checkable
class AuditPort(Protocol):
    """Record material boundary events without owning business rules."""

    def record(self, event: AuditRecord) -> None: ...


@runtime_checkable
class ObservationRepositoryPort(Protocol):
    """Durable canonical persistence boundary for observation revisions."""

    def latest(self, identity: "ObservationIdentity") -> "ObservationResult | None": ...

    def append(self, revision: "ObservationRevision") -> "ObservationResult": ...


__all__ = [
    "AccountStatePort", "AuditPort", "ConfirmationEnginePort", "DecisionEnginePort",
    "ExecutionHistoryPort", "ExecutionPort", "ExitExecutionPort", "GovernanceEnginePort",
    "GoverningKeyLevelPort", "H1MarketStructurePort", "InstrumentSpecificationPort",
    "KeyLevelEnginePort", "MarketDataPort", "MarketExecutionContextPort",
    "NoisePolicyPort", "ObservationQualificationContextPort", "ObservationRepositoryPort",
    "RiskEnginePort", "SetupClassifierPort", "TradeJournalPort", "VolatilityPolicyPort",
]
