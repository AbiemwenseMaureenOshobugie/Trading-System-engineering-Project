# MS-0.28 — Live Execution Contract

## Purpose

MS-0.28 adds the independent authority required before ASTER may submit a real-money broker order.

It extends, but does not replace, MS-0.27 runtime authorization.

```
Decision VALID
    +
Risk AUTHORIZED
    +
Governance AUTHORIZED
    +
MS-0.27 Runtime Execution Authorization
    +
MS-0.28 LiveExecutionAuthorization
    ↓
Live Broker Submission
```

Deployment capability is not live execution authorization.

## LE-D01 — Live Execution Authorization

ASTER requires a dedicated `LiveExecutionAuthorization` before real-money submission.

The authorization records:

- authorization identity;
- decision identity;
- instrument;
- authorized execution mode;
- runtime identity;
- runtime-context identity;
- operator authority identity;
- issuance time;
- explicit expiry time;
- current authorization status.

The authorization does not own strategy, risk, governance, position sizing, stop-loss, target, or broker decision logic.

## LE-D02 — Scope and Expiry

A live authorization is scoped to one decision, one instrument, one runtime,
one runtime context, and controlled-live execution mode.

Its validity window is:

```
authorized_at <= now < expires_at
```

No fixed duration is imposed. An expired authorization cannot be reused or automatically renewed.

## LE-D03 — Validity

At live submission the authorization must be ACTIVE, unexpired, and exactly match the decision, instrument, runtime, and runtime context.

Decision, Risk, Governance, and MS-0.27 runtime authorization remain independently required.

## LE-D04 — Issuance Authority

A live authorization is created only by an explicit operator authorization event.

Passing the strategy pipeline, selecting `CONTROLLED_LIVE`, or possessing broker credentials does not create live authority.

## LE-D05 — Issuance Mechanism

ASTER exposes an explicit control action that creates the authorization.

Authentication technology, UI technology, API technology, and deployment infrastructure are outside this contract.

## LE-D06 — Reuse

Each live authorization is single-use.

A consumed authorization cannot authorize another broker submission.

## LE-D07 — Consumption

The authorization is consumed atomically at the live execution-boundary submission attempt. Broker acceptance or rejection does not restore it.

## LE-D08 — Unknown Broker Outcome

If the broker outcome is unknown after the submission attempt:

- the authorization remains consumed;
- execution remains unresolved;
- ASTER must not automatically resubmit;
- reconciliation is required.

Unknown is never interpreted as success or failure.

## LE-D09 — Reconciliation Authority

Broker-side order/account state is authoritative. ASTER must not infer the outcome from a local timeout or connection failure.

## LE-D10 — Reconciliation Timing and Retry

ASTER may perform bounded, read-only reconciliation attempts. If authoritative evidence cannot be established, the execution is escalated to manual reconciliation.

Read-only reconciliation is not order-submission retry.

MS-0.28 does not prescribe retry count, interval, or timeout values.

## LE-D11 — Reconciliation Authority Boundary

While unresolved, ASTER may only query broker/account state, retrieve fill evidence,
update local evidence, emit audit events, and escalate reconciliation.

It may not submit, cancel, modify, or otherwise correct the unresolved order.

## LE-D12 — Canonical Broker Outcomes

Broker-native states normalize to:

- `PENDING`
- `PARTIALLY_FILLED`
- `FILLED`
- `REJECTED`
- `CANCELLED`
- `EXPIRED`
- `UNKNOWN`

`PENDING`, `PARTIALLY_FILLED`, and `UNKNOWN` remain unresolved.

`FILLED` resolves as ASTER `FILLED`.

`REJECTED`, `CANCELLED`, and `EXPIRED` resolve as ASTER `FAILED`.

## LE-D13 — Partial Fill

ASTER never independently submits an unfilled remainder. While the broker reports `PARTIALLY_FILLED`, ASTER waits for the broker's final disposition.

## LE-D14 — Final Partial-Fill Representation

Execution lifecycle and fill status are separate.

```
ExecutionState       = FAILED
requested_quantity   = 1000
executed_quantity    = 600
remaining_quantity   = 400
broker_outcome       = CANCELLED
fill_classification  = PARTIAL
```

## LE-D15 — Terminal Partial-Fill Outcome

The authoritative broker disposition is preserved separately from the derived fill classification.

Fill classification is:

- `NONE`
- `FULL`
- `PARTIAL`

## LE-D16 — FILLED State

ASTER enters `FILLED` only when the entire requested quantity has been executed.

## LE-D17 — Terminal Partial Fill

A partial fill followed by a terminal non-filled disposition is ASTER `FAILED` with `PARTIAL` fill classification.

## LE-D18 — Partial Fill With Unresolved Remainder

While the broker remains `PARTIALLY_FILLED` and the remainder is unresolved, ASTER keeps `ExecutionState = SUBMITTED`.

Requested, executed, and remaining quantities are recorded. Remaining quantity is informational/reconciliation state, not execution authority.

## Explicit Non-Decisions

MS-0.28 does not specify a broker vendor, SDK, authentication technology, control UI, cloud infrastructure, automatic submission retry, corrective execution during reconciliation, fixed authorization duration, or fixed reconciliation retry parameters.

## Acceptance Criteria

1. Live execution requires Decision, Risk, Governance, MS-0.27 runtime, and MS-0.28 live authorization.
2. Live authorization is explicitly operator-issued.
3. It is decision-, instrument-, runtime-, and runtime-context-scoped.
4. Expiry is explicit and enforced.
5. Authorization is single-use and consumed at the live submission boundary.
6. Unknown broker outcome never triggers automatic resubmission.
7. Broker-side state is authoritative during reconciliation.
8. Reconciliation is read-only.
9. Broker states normalize to the canonical vocabulary.
10. Partial fills do not authorize remainder submission.
11. `FILLED` requires full requested quantity.
12. Terminal partial fills are `FAILED` with `PARTIAL` classification.
13. Unresolved partial fills remain `SUBMITTED`.
14. Material live authorization, submission, and reconciliation events are auditable.
15. No MS-0.28 rule duplicates strategy, risk, governance, or MS-0.27 runtime policy.
