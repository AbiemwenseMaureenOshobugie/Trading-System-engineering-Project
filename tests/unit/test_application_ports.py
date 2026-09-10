from datetime import datetime, timezone

from trading_system.application import (
    AuditPort,
    ConfirmationEnginePort,
    DecisionEnginePort,
    ExecutionPort,
    GovernanceEnginePort,
    H1MarketStructurePort,
    KeyLevelEnginePort,
    MarketDataPort,
    RiskEnginePort,
    SetupClassifierPort,
)
from trading_system.domain import (
    GovernanceResult,
    MarketCandle,
    MarketStructureState,
    Regime,
    RiskResult,
    RiskStatus,
    GovernanceStatus,
    Timeframe,
)


def candle() -> MarketCandle:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=start,
        timestamp_close=start.replace(hour=11),
        open=1.1,
        high=1.11,
        low=1.09,
        close=1.105,
        source="test",
    )


class DataAdapter:
    def get_candles(self, *, symbol, timeframe, start, end):
        return [candle()]


class StructureEngine:
    def evaluate(self, candles):
        return MarketStructureState(
            regime=Regime.UNCLEAR,
            structure_version="0.1.0",
            evaluated_at=candles[-1].timestamp_close,
        )


class KeyLevels:
    def detect(self, *, candles, structure):
        return []


class ConfirmationEngine:
    def evaluate(self, *, candles, structure, key_levels):
        return []


class Classifier:
    def classify(self, confirmations):
        return []


class Risk:
    def assess(self, candidate):
        return RiskResult(
            decision_id=candidate.decision_id,
            status=RiskStatus.RISK_REJECTED,
            reason_codes=("TEST",),
        )


class Governance:
    def authorize(self, candidate):
        return GovernanceResult(
            decision_id=candidate.decision_id,
            instrument_session_eligible=True,
            daily_trade_count=0,
            daily_loss_count=0,
            checks=("TEST",),
            status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        )


class Decision:
    def evaluate(self, *, candidate, risk, governance):
        return "BLOCKED"


class Execution:
    def submit(self, *, candidate, risk, governance):
        raise NotImplementedError


class Audit:
    def record(self, event):
        return None


def test_ports_are_runtime_compatible_with_structural_implementations():
    implementations = [
        (MarketDataPort, DataAdapter()),
        (H1MarketStructurePort, StructureEngine()),
        (KeyLevelEnginePort, KeyLevels()),
        (ConfirmationEnginePort, ConfirmationEngine()),
        (SetupClassifierPort, Classifier()),
        (RiskEnginePort, Risk()),
        (GovernanceEnginePort, Governance()),
        (DecisionEnginePort, Decision()),
        (ExecutionPort, Execution()),
        (AuditPort, Audit()),
    ]

    for protocol, implementation in implementations:
        assert isinstance(implementation, protocol)
