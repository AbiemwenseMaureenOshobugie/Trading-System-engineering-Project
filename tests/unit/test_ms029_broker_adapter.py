"""MS-0.29 broker adapter contract tests."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.domain import (
    BrokerDiscoveryOutcome,
    BrokerDiscoveryRequest,
    BrokerDiscoveryResult,
    BrokerEvidence,
    BrokerOrderOutcome,
    BrokerOrderRequest,
    BrokerOrderSnapshot,
    BrokerPositionSnapshot,
    BrokerPositionSyncOutcome,
    BrokerSubmissionResult,
    Direction,
    TransmissionStatus,
)
from trading_system.execution.broker import BrokerAdapterBoundary, BrokerPositionSynchronizer

NOW = datetime(2026, 10, 8, 10, 0, tzinfo=timezone.utc)


def request() -> BrokerOrderRequest:
    return BrokerOrderRequest(
        "D-1", "LEA-D-1", "EURUSD", Direction.BUY, Decimal("1000"), Decimal("1.1000")
    )


def snapshot(outcome=BrokerOrderOutcome.PENDING) -> BrokerOrderSnapshot:
    executed = Decimal("0") if outcome is BrokerOrderOutcome.PENDING else Decimal("1000")
    price = None if executed == 0 else Decimal("1.1001")
    return BrokerOrderSnapshot(
        "BO-1", outcome, Decimal("1000"), executed, price, outcome.value, NOW, "BE-1"
    )


def evidence(outcome=BrokerOrderOutcome.PENDING) -> BrokerEvidence:
    return BrokerEvidence(
        "BE-1", "test-broker", "test-adapter", "1.0",
        outcome.value, None, outcome, NOW
    )


def test_broker_request_is_strategy_agnostic():
    result = request()
    assert result.decision_id == "D-1"
    assert result.authorization_id == "LEA-D-1"


def test_submission_transmission_status_is_independent():
    for status in TransmissionStatus:
        result = BrokerSubmissionResult(
            status,
            snapshot() if status is TransmissionStatus.TRANSMITTED else None,
            evidence() if status is not TransmissionStatus.NOT_TRANSMITTED else None,
        )
        BrokerAdapterBoundary.validate_submission(request(), result)


def test_not_transmitted_cannot_contain_evidence():
    with pytest.raises(ValueError):
        BrokerSubmissionResult(TransmissionStatus.NOT_TRANSMITTED, snapshot(), evidence())


def test_discovery_unique_match_requires_snapshot():
    result = BrokerDiscoveryResult(BrokerDiscoveryOutcome.UNIQUE_MATCH, snapshot(), evidence())
    BrokerAdapterBoundary.validate_discovery(result)


def test_discovery_cannot_select_ambiguous_match():
    with pytest.raises(ValueError):
        BrokerDiscoveryResult(BrokerDiscoveryOutcome.AMBIGUOUS_MATCH, snapshot(), evidence())


def test_discovery_request_uses_authorization_identity_only():
    assert BrokerDiscoveryRequest("LEA-D-1").authorization_id == "LEA-D-1"


def test_position_match_requires_authoritative_identity():
    position = BrokerPositionSnapshot(
        "BP-1", "EURUSD", Direction.BUY, Decimal("1000"), Decimal("1.1000"), NOW, "BE-2"
    )
    result = BrokerPositionSynchronizer.synchronize(
        known_broker_position_id="BP-1", snapshots=(position,)
    )
    assert result.outcome is BrokerPositionSyncOutcome.MATCH


def test_unknown_broker_position_is_not_attributed():
    position = BrokerPositionSnapshot(
        "BP-2", "EURUSD", Direction.BUY, Decimal("1000"), Decimal("1.1000"), NOW
    )
    result = BrokerPositionSynchronizer.synchronize(
        known_broker_position_id=None, snapshots=(position,)
    )
    assert result.outcome is BrokerPositionSyncOutcome.UNKNOWN_BROKER_POSITION


def test_missing_broker_position_is_not_a_close():
    result = BrokerPositionSynchronizer.synchronize(
        known_broker_position_id="BP-1", snapshots=()
    )
    assert result.outcome is BrokerPositionSyncOutcome.BROKER_POSITION_MISSING


def test_ambiguous_position_match_is_not_selected():
    second = BrokerPositionSnapshot(
        "BP-2", "EURUSD", Direction.BUY, Decimal("500"), Decimal("1.1002"), NOW
    )
    result = BrokerPositionSynchronizer.synchronize(
        known_broker_position_id=None, snapshots=(position, second)
    )
    assert result.outcome is BrokerPositionSyncOutcome.AMBIGUOUS_MATCH
