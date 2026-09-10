# ADR 0002: Application Boundary Corrections Before MS-0.1A

- **Status:** Accepted
- **Date:** 2026-09-10
- **Decision scope:** MS-0.2D application boundaries

## Context

Before implementing the H1 Market Structure Engine (MS-0.1A), the application-layer contracts were audited for architectural weaknesses that could create look-ahead, authorization, or dependency-boundary problems later.

The audit identified four related concerns:

1. `DecisionEnginePort` exposed an untyped `str` result even though the final decision contract had not been formally specified.
2. `ExecutionPort` documented downstream authorization but did not make the authorization precondition sufficiently explicit.
3. The data flow did not explicitly protect strategy engines from raw provider data.
4. `H1MarketStructurePort` had no explicit evaluation boundary, leaving room for accidental use of future candles in replay or backtesting.

The MS-0.2D protocol test also contained fixtures that no longer matched the required fields of the canonical domain models.

## Decision

We will:

- remove the deferred `DecisionEnginePort` from the executable application port set until a typed final decision contract is formally defined;
- keep `ExecutionPort` as a boundary that accepts Risk and Governance results, with concrete implementations required to reject anything other than authorized control results;
- explicitly require the data pipeline to transform external/provider records through adapter, validation, and normalization stages before producing canonical `MarketCandle` objects consumed by strategy code;
- require H1 structure evaluation to receive an explicit `evaluation_cutoff` and define the result as structure as of that boundary, using only completed candles at or before the cutoff;
- correct protocol-test fixtures to match the current immutable domain contracts;
- document these boundaries without introducing unresolved strategy semantics or premature domain abstractions.

## Consequences

### Positive

- The application layer no longer exposes a misleading temporary decision type.
- Strategy code has a clear canonical-data boundary.
- H1 evaluation has an explicit mechanism for preventing look-ahead bias.
- Execution remains downstream of Risk and Governance rather than becoming a second decision-maker.
- Tests remain aligned with the actual domain contracts.

### Deferred

The following remain intentionally unspecified:

- the final typed decision outcome;
- concrete validation and normalization result objects;
- broker/MT5 adapter contracts;
- persistence contracts;
- explanation and analytics service contracts.

These will be introduced only when their semantics are formally required.

## Rejected alternatives

### Keep `DecisionEnginePort -> str`

Rejected because a string is not a meaningful canonical contract and permits accidental creation of unsupported states.

### Invent a final decision enum now

Rejected because the decision-state semantics have not yet been frozen as a domain contract.

### Put risk/governance authorization rules into `ExecutionPort`

Rejected because ports define dependency boundaries; concrete execution implementations must enforce the authorization precondition without moving business rules into the interface.

### Let H1 infer the evaluation boundary from the last supplied candle

Rejected because an implicit boundary is unsafe for replay/backtesting and makes accidental future-candle contamination easier.
