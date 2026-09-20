# MS-0.7 — Execution-State and Paper-Execution Contract

## Purpose

MS-0.7 defines the smallest deterministic execution contract needed after a
Decision Engine returns an authorized VALID outcome. It does not introduce
new strategy, risk, governance, broker, or market-microstructure rules.

## Authorization

Execution requires all three independently verifiable outcomes:

- DecisionStatus.VALID
- RiskStatus.RISK_AUTHORIZED
- GovernanceStatus.GOVERNANCE_AUTHORIZED

Execution verifies these typed status fields directly. Reason codes are
explanatory/audit data and are not authorization signals.

## Canonical lifecycle

The lifecycle is strict and forward-only:

AUTHORIZED -> SUBMITTED -> FILLED
                       \-> FAILED

FILLED and FAILED are terminal. Execution records cannot be reopened or moved
backward.

The canonical domain deliberately excludes broker-specific states such as
partial fill, cancellation, expiry, or broker rejection. Such states remain
adapter-level concerns until separately specified.

## Paper representation

Paper execution contains an explicit PaperOrder and PaperFill.

PaperOrder represents the execution request after authorization and submission.
Required information:
- order identity
- decision identity
- symbol
- direction
- requested entry price
- requested quantity
- submission timestamp

PaperFill represents the simulated execution result.
Required information:
- fill identity
- order identity
- fill price
- executed quantity
- execution timestamp

## Paper fill semantics

For the initial deterministic paper implementation:

PaperFill.fill_price == PaperOrder.requested_entry_price

Submission immediately produces a fill.

No spread, slippage, latency, liquidity, bid/ask, partial-fill, or price-touch
model is introduced.

## Failure semantics

FAILED represents execution/infrastructure failure only. It is never a new
strategy, risk, governance, or decision outcome.

## Audit contract

Every canonical execution-state transition produces an immutable audit event:

- EXECUTION_AUTHORIZED
- EXECUTION_SUBMITTED
- EXECUTION_FILLED
- EXECUTION_FAILED

Events reference the execution identity and decision identity and preserve the
transition timestamp and resulting state.

## Boundary

The execution layer:
- verifies authorization;
- creates/submits the paper order;
- creates the deterministic paper fill;
- records execution-state audit events.

It does not:
- recalculate strategy;
- recalculate risk;
- re-evaluate governance;
- modify the requested entry price;
- create another decision.

## Signal, order, and fill remain distinct

A strategy signal remains represented by DecisionCandidate. A PaperOrder
represents the submitted execution request. A PaperFill represents the
execution result.

A VALID decision is therefore not equivalent to a fill. FILLED is a downstream
execution outcome. FAILED does not invalidate or reinterpret the preceding
decision.
