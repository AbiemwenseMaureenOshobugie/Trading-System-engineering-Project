# MS-0.29 — Live Execution Runtime & Broker Adapter Contract

## Purpose

MS-0.29 establishes the broker-agnostic operational boundary through which an already-authorized live execution becomes a broker order and through which ASTER establishes authoritative broker state.

No strategy, risk, governance, live-authorization, or execution-authority rule is introduced.

## BE-D01 — Broker Adapter Boundary

ASTER exposes separate broker command and read boundaries:

- `BrokerSubmissionPort` — order submission.
- `BrokerReadPort` — read-only broker-order reconciliation.
- `BrokerDiscoveryPort` — execution-scoped, read-only discovery.
- `BrokerPositionReadPort` — read-only broker-position state.

Broker adapters receive broker-neutral contracts. They do not receive `DecisionCandidate`.

## BE-D02 — Order Submission Contract

Submission uses `BrokerOrderRequest`, carrying only already-authorized execution intent. Broker-native mechanics remain inside the adapter.

## BE-D03 — Response Normalization

Adapters normalize native responses to the existing canonical outcomes:

`PENDING`, `PARTIALLY_FILLED`, `FILLED`, `REJECTED`, `CANCELLED`, `EXPIRED`, `UNKNOWN`.

Ambiguous evidence is handled conservatively.

## BE-D04 — Submission vs Broker Order

A submission attempt is distinct from a broker order. `broker_order_id` is authoritative only when supplied by broker evidence. ASTER never synthesizes it.

## BE-D05 — BrokerOrderRequest

Fields:

- `decision_id`
- `authorization_id`
- `symbol`
- `direction`
- `requested_quantity`
- `requested_entry_price`

The entry price is a reference only and does not prescribe MARKET/LIMIT/STOP mechanics.

## BE-D06 — Failure and Recovery

`NOT_TRANSMITTED` is permitted only when reliable evidence establishes that the broker was not reached.

If the request may have reached the broker, transmission status is `UNKNOWN`.

An explicit broker rejection is represented by canonical broker outcome `REJECTED`.

No failure authorizes automatic resubmission.

## BE-D07 — BrokerSubmissionResult

Submission returns a dedicated result separating transmission certainty from broker-order evidence.

Transmission status is one of:

- `NOT_TRANSMITTED`
- `TRANSMITTED`
- `UNKNOWN`

Transmission status is not a broker-order state.

## BE-D08 — Submission Result Semantics

Broker evidence is optional.

`NOT_TRANSMITTED` cannot carry broker-order evidence.

`UNKNOWN` never means rejection, success, or retry permission.

## BE-D09 — Broker Evidence

Broker-native evidence is diagnostic/audit data only.

`BrokerOrderSnapshot.evidence_ref` may reference ASTER-owned evidence identity.

## BE-D10 — Evidence Identity

ASTER owns evidence identity. Native identifiers, status codes, adapter identity/version, and captured details remain evidence attributes.

## BE-D11 — Discovery

Unknown submissions may use deterministic, read-only, execution-scoped discovery using `authorization_id`.

Discovery cannot submit, modify, cancel, or retry broker orders.

## BE-D12 — Discovery Result

Discovery returns:

- `UNIQUE_MATCH`
- `NO_MATCH`
- `AMBIGUOUS_MATCH`

Only `UNIQUE_MATCH` may contain a selected snapshot.

## BE-D13 — Discovery Identity

Discovery requests use `authorization_id` only.

## BE-D14 — Post-Discovery Reconciliation

Discovery establishes broker-order identity; normal read-only reconciliation establishes current broker state.

No-match and ambiguous-match remain unresolved.

## BE-D15 — Reconciliation Attempts

Reconciliation is bounded and read-only. Runtime policy determines reconciliation opportunities. It never resubmits an order.

## BE-D16 — Terminality

`FILLED` requires full requested quantity.

`REJECTED`, `CANCELLED`, and `EXPIRED` resolve to `FAILED`.

`PENDING`, `PARTIALLY_FILLED`, and `UNKNOWN` remain unresolved.

Reconciliation exhaustion does not itself create a trading outcome.

## BE-D17 — Scheduling

Reconciliation scheduling is runtime-owned. No fixed interval or retry count is introduced here.

## BE-D18 — Position Synchronization

Broker position state is authoritative and read-only.

`broker_position_id` is authoritative when supplied.

Unmatched or ambiguous broker positions are discrepancies, not strategy positions.

Position synchronization never submits, modifies, or closes broker positions.

## MT5

The broker-neutral contract is frozen before vendor-specific mechanics. A later MT5 adapter must implement these ports without leaking MT5 semantics into the canonical domain.

## Acceptance Criteria

1. Broker submission no longer receives a strategy `DecisionCandidate`.
2. Broker submission receives a broker-neutral `BrokerOrderRequest`.
3. Submission certainty is distinct from broker order outcome.
4. Broker order identity comes only from broker evidence.
5. Broker-native evidence remains non-authoritative diagnostic data.
6. Unknown submissions cannot be blindly retried.
7. Discovery is read-only, execution-scoped, and uses `authorization_id`.
8. Discovery never selects among ambiguous matches.
9. Reconciliation establishes broker order state after identity is known.
10. Position synchronization is broker-authoritative and read-only.
11. No new strategy/risk/governance logic is introduced.
