"""Broker-neutral live execution boundary services for MS-0.29."""

from __future__ import annotations

from decimal import Decimal

from trading_system.domain import (
    BrokerDiscoveryOutcome,
    BrokerDiscoveryResult,
    BrokerOrderRequest,
    BrokerPositionSnapshot,
    BrokerPositionSyncOutcome,
    BrokerPositionSyncResult,
    BrokerSubmissionResult,
    TransmissionStatus,
)


class BrokerContractError(RuntimeError):
    """Raised when a broker adapter violates the canonical MS-0.29 contract."""


class BrokerAdapterBoundary:
    """Validate broker submission/discovery evidence without trading logic."""

    VERSION = "MS-0.29"

    @staticmethod
    def validate_submission(request: BrokerOrderRequest, result: BrokerSubmissionResult) -> None:
        if result.transmission_status is TransmissionStatus.NOT_TRANSMITTED:
            if result.snapshot is not None or result.evidence is not None:
                raise BrokerContractError("NOT_TRANSMITTED cannot carry broker evidence")
            return
        if result.snapshot is not None:
            if result.snapshot.requested_quantity != request.requested_quantity:
                raise BrokerContractError("broker requested quantity mismatch")
            if not result.snapshot.broker_order_id.strip():
                raise BrokerContractError("broker order identity must not be blank")

    @staticmethod
    def validate_discovery(result: BrokerDiscoveryResult) -> None:
        if result.outcome is BrokerDiscoveryOutcome.UNIQUE_MATCH and result.snapshot is None:
            raise BrokerContractError("UNIQUE_MATCH requires exactly one snapshot")
        if result.outcome is not BrokerDiscoveryOutcome.UNIQUE_MATCH and result.snapshot is not None:
            raise BrokerContractError("discovery may not select a snapshot for non-unique outcomes")


class BrokerPositionSynchronizer:
    """Compare broker-authoritative evidence with an established ASTER identity."""

    @staticmethod
    def synchronize(
        *,
        known_broker_position_id: str | None,
        snapshot: BrokerPositionSnapshot | None,
        ambiguous: bool = False,
    ) -> BrokerPositionSyncResult:
        if ambiguous:
            return BrokerPositionSyncResult(
                BrokerPositionSyncOutcome.AMBIGUOUS_MATCH,
                None,
                "multiple broker positions cannot be attributed automatically",
            )
        if snapshot is None:
            return BrokerPositionSyncResult(
                BrokerPositionSyncOutcome.BROKER_POSITION_MISSING,
                None,
                "no authoritative broker position was observed",
            )
        if known_broker_position_id is None:
            return BrokerPositionSyncResult(
                BrokerPositionSyncOutcome.UNKNOWN_BROKER_POSITION,
                snapshot,
                "broker position identity is not associated with an ASTER position",
            )
        if snapshot.broker_position_id != known_broker_position_id:
            return BrokerPositionSyncResult(
                BrokerPositionSyncOutcome.UNKNOWN_BROKER_POSITION,
                snapshot,
                "broker position identity does not match the established ASTER identity",
            )
        return BrokerPositionSyncResult(BrokerPositionSyncOutcome.MATCH, snapshot)


def build_broker_order_request(
    *,
    decision_id: str,
    authorization_id: str,
    symbol: str,
    direction,
    requested_quantity: Decimal,
    requested_entry_price: Decimal,
) -> BrokerOrderRequest:
    return BrokerOrderRequest(
        decision_id=decision_id,
        authorization_id=authorization_id,
        symbol=symbol,
        direction=direction,
        requested_quantity=requested_quantity,
        requested_entry_price=requested_entry_price,
    )
