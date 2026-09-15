from datetime import datetime, timezone
from decimal import Decimal

from trading_system.application import (
    AuditPort,
    ConfirmationEnginePort,
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
    GovernanceStatus,
    MarketCandle,
    MarketStructureState,
    Regime,
    RiskResult,
    RiskStatus,
    Timeframe,
)


def candle() -> MarketCandle:
    start = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=start,
        timestamp_close=start.replace(hour=11),
        open=Decimal("1.10"),
        high=Decimal("1.11"),
        low=Decimal("1.09"),
        close=Decimal("1.105"),
        source="test",
    )


class DataAdapter:
    def get_candles(self, *, symbol, timeframe, start, end):
        return [candle()]


class StructureEngine:
    def evaluate(self, *, candles, evaluation_cutoff):
        return MarketStructureState(
            regime=Regime.UNCLEAR,
            structure_version="0.1.0",
            meaningful_highs=(),
            meaningful_lows=(),
            controlling_level=None,
            range_upper_boundary=None,
            range_lower_boundary=None,
            structural_events=(),
            evaluated_at=evaluation_cutoff,
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
            requested_risk=None,
            approved_risk=None,
            position_size=None,
            entry_assumption=None,
            stop_distance=None,
            target_distance=None,
            risk_reward=None,
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
            reason_codes=(),
        )


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
        (ExecutionPort, Execution()),
        (AuditPort, Audit()),
    ]

    for protocol, implementation in implementations:
        assert isinstance(implementation, protocol)


def test_h1_port_requires_an_explicit_evaluation_cutoff():
    engine = StructureEngine()
    cutoff = candle().timestamp_close

    state = engine.evaluate(candles=[candle()], evaluation_cutoff=cutoff)

    assert state.evaluated_at == cutoff
