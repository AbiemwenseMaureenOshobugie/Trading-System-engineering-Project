"""Canonical immutable domain models for the trading system.

These models describe data exchanged between components. They do not implement
trading decisions, setup detection, risk calculations, governance rules, or
broker behavior.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .enums import (
    ConfirmationType,
    DecisionStatus,
    Direction,
    ExecutionState,
    GovernanceStatus,
    KeyLevelSource,
    Regime,
    RiskStatus,
    SwingKind,
    Timeframe,
)


@dataclass(frozen=True, slots=True)
class MarketCandle:
    """One completed OHLC candle from an external market-data source."""

    symbol: str
    timeframe: Timeframe
    timestamp_open: datetime
    timestamp_close: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Optional[Decimal] = None
    source: str = ""

    def __post_init__(self) -> None:
        if self.timestamp_open.tzinfo is None or self.timestamp_close.tzinfo is None:
            raise ValueError("candle timestamps must be timezone-aware")
        if self.timestamp_open >= self.timestamp_close:
            raise ValueError("timestamp_open must be earlier than timestamp_close")
        if self.high < max(self.open, self.close):
            raise ValueError("high must be greater than or equal to open and close")
        if self.low > min(self.open, self.close):
            raise ValueError("low must be less than or equal to open and close")


@dataclass(frozen=True, slots=True)
class SwingPoint:
    """A meaningful structural high or low identified by a strategy engine."""

    timestamp: datetime
    price: Decimal
    kind: SwingKind


@dataclass(frozen=True, slots=True)
class PriceZone:
    """A price interval representing a zone rather than a single price line."""

    lower: Decimal
    upper: Decimal

    def __post_init__(self) -> None:
        if self.lower > self.upper:
            raise ValueError("zone lower bound must not exceed upper bound")


@dataclass(frozen=True, slots=True)
class MarketStructureState:
    """Snapshot of the H1 structural classification and its evidence."""

    regime: Regime
    structure_version: str
    meaningful_highs: tuple[SwingPoint, ...]
    meaningful_lows: tuple[SwingPoint, ...]
    controlling_level: Optional[SwingPoint]
    range_upper_boundary: Optional[PriceZone]
    range_lower_boundary: Optional[PriceZone]
    structural_events: tuple[str, ...]
    evaluated_at: datetime


@dataclass(frozen=True, slots=True)
class KeyLevel:
    """Canonical structural Key-Level identity with source-specific zones."""

    key_level_id: str
    source_types: tuple[KeyLevelSource, ...]
    source_zones: tuple[tuple[KeyLevelSource, PriceZone], ...]
    active: bool
    role: Optional[str]
    created_at: datetime
    updated_at: datetime
    evidence_refs: tuple[str, ...]
    state_history: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ConfirmationSequence:
    """Active or completed CP-1/CP-2 confirmation process."""

    setup_id: str
    confirmation_type: ConfirmationType
    direction: Direction
    setup_key_level: str
    state: str
    candle_refs: tuple[str, ...]
    controlling_extreme: Optional[Decimal]
    signal_status: str
    invalidation_reason: Optional[str]


@dataclass(frozen=True, slots=True)
class DecisionCandidate:
    """Strategy-qualified candidate before risk and governance authorization."""

    decision_id: str
    strategy_version: str
    symbol: str
    direction: Direction
    setup_type: ConfirmationType
    setup_id: str
    signal_timestamp: datetime
    signal_entry_price: Decimal
    proposed_stop_loss: Optional[Decimal]
    proposed_target: Optional[Decimal]
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RiskRequest:
    """Inputs required by the Risk Engine to qualify and size one candidate."""

    candidate: DecisionCandidate
    active_key_levels: tuple[KeyLevel, ...]
    setup_key_level_id: Optional[str]
    account_equity: Decimal
    spread: Decimal
    slippage: Decimal
    noise: Decimal
    volatility_adjustment: Decimal
    value_per_price_unit: Decimal

    def __post_init__(self) -> None:
        if self.account_equity <= 0:
            raise ValueError("account_equity must be positive")
        for name, value in (
            ("spread", self.spread),
            ("slippage", self.slippage),
            ("noise", self.noise),
            ("volatility_adjustment", self.volatility_adjustment),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if self.value_per_price_unit <= 0:
            raise ValueError("value_per_price_unit must be positive")


@dataclass(frozen=True, slots=True)
class RiskResult:
    """Independent outcome produced by the Risk Engine."""

    decision_id: str
    requested_risk: Optional[Decimal]
    approved_risk: Optional[Decimal]
    position_size: Optional[Decimal]
    entry_assumption: Optional[Decimal]
    structural_stop_loss: Optional[Decimal]
    final_stop_loss: Optional[Decimal]
    target_price: Optional[Decimal]
    stop_distance: Optional[Decimal]
    target_distance: Optional[Decimal]
    risk_reward: Optional[Decimal]
    risk_amount: Optional[Decimal]
    status: RiskStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class GovernanceRequest:
    """Inputs required by the Governance Engine to authorize one candidate."""

    candidate: DecisionCandidate
    instrument_session_eligible: bool
    daily_trade_count: int
    daily_loss_count: int

    def __post_init__(self) -> None:
        if self.daily_trade_count < 0:
            raise ValueError("daily_trade_count must not be negative")
        if self.daily_loss_count < 0:
            raise ValueError("daily_loss_count must not be negative")


@dataclass(frozen=True, slots=True)
class GovernanceResult:
    """Independent outcome produced by the Governance Engine."""

    decision_id: str
    instrument_session_eligible: bool
    daily_trade_count: int
    daily_loss_count: int
    checks: tuple[str, ...]
    status: GovernanceStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DecisionRequest:
    """Inputs used by the Decision Engine to aggregate upstream outcomes."""

    candidate: Optional[DecisionCandidate]
    strategy_pending: bool
    risk_result: Optional[RiskResult]
    governance_result: Optional[GovernanceResult]

    def __post_init__(self) -> None:
        if self.candidate is None and self.risk_result is not None:
            raise ValueError("risk_result requires a candidate")
        if self.candidate is None and self.governance_result is not None:
            raise ValueError("governance_result requires a candidate")


@dataclass(frozen=True, slots=True)
class DecisionResult:
    """Final deterministic decision state before execution."""

    decision_id: Optional[str]
    status: DecisionStatus
    reason_codes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PaperOrder:
    """Deterministic paper execution request."""

    order_id: str
    decision_id: str
    symbol: str
    direction: Direction
    requested_entry_price: Decimal
    requested_quantity: Decimal
    submission_timestamp: datetime


@dataclass(frozen=True, slots=True)
class PaperFill:
    """Deterministic paper execution result."""

    fill_id: str
    order_id: str
    fill_price: Decimal
    executed_quantity: Decimal
    execution_timestamp: datetime


@dataclass(frozen=True, slots=True)
class ExecutionRecord:
    """Immutable execution outcome kept separate from the strategy signal."""

    execution_id: str
    decision_id: str
    state: ExecutionState
    order_id: str
    fill_id: Optional[str]
    order: PaperOrder
    fill: Optional[PaperFill]
    failure_reason: Optional[str]


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """Immutable trace record for a material system event or decision boundary."""

    audit_id: str
    timestamp: datetime
    event_type: str
    strategy_version: str
    decision_id: Optional[str]
    payload_refs: tuple[str, ...]
    outcome: Optional[str]


@dataclass(frozen=True, slots=True)
class Position:
    """Open position created from an actual entry execution."""
    position_id: str
    decision_id: str
    entry_execution_id: str
    symbol: str
    direction: Direction
    open_quantity: Decimal
    entry_execution_price: Decimal
    entry_execution_timestamp: datetime
    def __post_init__(self) -> None:
        if self.open_quantity <= 0: raise ValueError("open_quantity must be positive")
        if self.entry_execution_timestamp.tzinfo is None: raise ValueError("entry_execution_timestamp must be timezone-aware")

@dataclass(frozen=True, slots=True)
class ExitInstruction:
    """Authorized instruction to close an existing position."""
    exit_instruction_id: str
    position_id: str
    decision_id: str
    symbol: str
    direction: Direction
    exit_type: ExitType
    requested_quantity: Decimal
    trigger_price: Decimal
    created_timestamp: datetime
    source_reference: str
    def __post_init__(self) -> None:
        if self.requested_quantity <= 0: raise ValueError("requested_quantity must be positive")
        if self.created_timestamp.tzinfo is None: raise ValueError("created_timestamp must be timezone-aware")

@dataclass(frozen=True, slots=True)
class ExitPaperFill:
    """Deterministic paper exit execution evidence."""
    exit_fill_id: str
    exit_instruction_id: str
    actual_exit_price: Decimal
    executed_quantity: Decimal
    exit_execution_timestamp: datetime
    def __post_init__(self) -> None:
        if self.executed_quantity <= 0: raise ValueError("executed_quantity must be positive")
        if self.exit_execution_timestamp.tzinfo is None: raise ValueError("exit_execution_timestamp must be timezone-aware")

@dataclass(frozen=True, slots=True)
class ExitExecutionRecord:
    """Immutable exit execution outcome."""
    exit_execution_id: str
    position_id: str
    decision_id: str
    state: ExitExecutionState
    instruction: ExitInstruction
    fill: Optional[ExitPaperFill]
    failure_reason: Optional[str]
    failure_timestamp: Optional[datetime]
