"""Application-layer ports and the canonical composition root."""

from .composition import CompositionDependencies, CompositionGapError, compose_runtime
from .ports import (
    AuditPort,
    ConfirmationEnginePort,
    DecisionEnginePort,
    ExecutionPort,
    ExitExecutionPort,
    GovernanceEnginePort,
    H1MarketStructurePort,
    KeyLevelEnginePort,
    MarketDataPort,
    ObservationRepositoryPort,
    RiskEnginePort,
    SetupClassifierPort,
    TradeJournalPort,
)

__all__ = [
    "AuditPort",
    "CompositionDependencies",
    "CompositionGapError",
    "ConfirmationEnginePort",
    "DecisionEnginePort",
    "ExecutionPort",
    "ExitExecutionPort",
    "GovernanceEnginePort",
    "H1MarketStructurePort",
    "KeyLevelEnginePort",
    "MarketDataPort",
    "ObservationRepositoryPort",
    "RiskEnginePort",
    "SetupClassifierPort",
    "TradeJournalPort",
    "compose_runtime",
]
