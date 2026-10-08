# MS-0.30 — MT5 Concrete Broker Adapter

## Status

Implementation boundary for the first concrete adapter of the broker-neutral MS-0.29 contract.

MS-0.30 does not modify strategy, risk, governance, live authorization, or execution authority.

## Frozen boundary

The MT5 adapter implements:
- BrokerSubmissionPort
- BrokerReadPort
- BrokerDiscoveryPort
- BrokerPositionReadPort

The adapter receives only broker-neutral contracts. It does not receive DecisionCandidate, RiskResult, GovernanceResult, or DecisionResult.

## MT5 responsibilities

1. Manage MT5 terminal/account connection.
2. Map canonical symbols to broker symbols using explicit configuration.
3. Validate requested quantity against MT5 volume constraints.
4. Translate BrokerOrderRequest into a market-deal request.
5. Use order_check before order_send.
6. Normalize native trade results into BrokerOrderOutcome.
7. Preserve MT5-native identifiers/status/retcodes as BrokerEvidence.
8. Read active and historical orders for reconciliation.
9. Perform execution-scoped discovery using authorization_id.
10. Read broker-authoritative positions.

## Transmission

- Preflight rejection: NOT_TRANSMITTED.
- order_send returns broker evidence: TRANSMITTED.
- order_send exception/no reliable broker evidence: UNKNOWN.
- UNKNOWN never triggers retry.

## Market execution

requested_entry_price remains reference evidence. The adapter uses the current MT5 bid/ask required to construct the market-deal request; the resulting execution price is broker evidence.

## Quantity

No upward rounding is performed. Values outside broker min/max/step constraints are rejected.

## Filling mode

The adapter receives an explicit configured MT5 filling mode and rejects it when the broker symbol does not support it.

## Discovery

The authorization identifier is encoded in the adapter-owned order comment marker. Discovery scans active and bounded historical orders for that exact marker.

- one unique broker order: UNIQUE_MATCH
- none: NO_MATCH
- multiple: AMBIGUOUS_MATCH

Ambiguous discovery never selects an order.

## Position state

MT5 position state is read-only and broker-authoritative. The adapter never infers an ASTER position from symbol alone.

## Non-goals

No automatic retry/resubmission, reconciliation scheduling, portfolio control, strategy logic, risk logic, governance logic, or new execution authority is introduced.
