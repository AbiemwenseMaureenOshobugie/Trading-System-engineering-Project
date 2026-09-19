"""Canonical immutable domain models for the trading system.

These models describe data exchanged between components. They do not implement
trading decisions, setup detection, risk calculations, or execution behavior.
"""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional

from .enums import (
    ConfirmationType,
    DecisionStatus,
    Direction,
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
class ExecutionRecord:
    """Broker execution record kept separate from the strategy signal."""

    decision_id: str
    order_submission_timestamp: datetime
    broker_order_id: Optional[str]
    requested_order_details: tuple[str, ...]
    execution_timestamp: Optional[datetime]
    execution_entry_price: Optional[Decimal]
    executed_quantity: Optional[Decimal]
    slippage: Optional[Decimal]
    broker_status: str


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """Trace record for a material system event or decision boundary."""

    audit_id: str
    timestamp: datetime
    event_type: str
    strategy_version: str
    decision_id: Optional[str]
    payload_refs: tuple[str, ...]
    outcome: Optional[str]
