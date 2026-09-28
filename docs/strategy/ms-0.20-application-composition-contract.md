# MS-0.20 — Application Composition Contract

## Status

**Contract frozen.**

MS-0.20 defines the single application composition root for the ASTER runtime.

## Contract

ASTER uses one typed composition operation:

`trading_system.application.composition.compose_runtime`

It constructs and wires the application dependency graph and returns an already-wired `RuntimeControl`.

The composition root:

- owns dependency construction and wiring;
- uses `RuntimeConfig` for operational configuration;
- maps concrete implementations to existing ports;
- constructs the runtime graph from market data through observation lifecycle and runtime control;
- constructs the execution boundary as part of the application graph;
- contains no trading/business rules;
- does not duplicate `RuntimeControl` lifecycle semantics;
- does not introduce a generic dependency-injection framework;
- is the authoritative construction mechanism.

The runtime entrypoint delegates to this composition root.

## Canonical graph

```text
RuntimeConfig
    |
    v
Application Composition Root
    |
    +-- Market Data
    +-- Observation Persistence
    +-- H1 Boundary / History
    +-- H1 Structure
    +-- Key Levels
    +-- Governing Key-Level Selection
    +-- M15 Confirmation
    +-- Setup Classification
    +-- Risk
    +-- Governance
    +-- Decision
    +-- Execution
    +-- Audit
    +-- Qualification / Context
            |
            v
    ObservationRunner
            |
            v
ObservationLifecycleCoordinator
            |
            v
      RuntimeControl
            |
            v
      RuntimeScheduler
```

## Explicit composition gaps

The repository at the MS-0.20 baseline does not contain production implementations for:

1. governing Key-Level selection;
2. setup classification;
3. qualification context required to construct Risk/Governance requests;
4. an external credential-resolution mechanism for provider credentials.

These are **composition gaps**, not places for placeholder trading behavior.

The composition root therefore accepts these dependencies through one typed `CompositionDependencies` value. No generic DI container is introduced. If required dependencies are absent, `compose_runtime` raises `CompositionGapError` with the missing capability names rather than silently constructing a fake implementation.

This is intentional fail-closed behavior.

## Concrete components assembled by the root

Where implementations already exist, the root constructs them directly:

- `TwelveDataMarketDataAdapter`
- `SQLiteObservationRepository`
- `MarketDataH1BoundaryResolver`
- `ExplicitObservationHistoryResolver`
- `H1MarketStructureEngine`
- `KeyLevelDetectionEngine`
- `M15ConfirmationEngine`
- `RiskEngine`
- `GovernanceEngine`
- `DecisionEngine`
- `ExecutionEngine`
- `ObservationRunner`
- `ObservationLifecycleCoordinator`
- `FileRuntimeOwnership`
- `RuntimeControl`
- `RuntimeScheduler`

## Authority boundary

The composition root wires components; it never decides:

- market structure;
- Key-Level meaning;
- confirmation validity;
- risk;
- governance;
- decision state;
- execution authorization;
- observation lifecycle state.

Those remain owned by their existing components.

## Entry point

`python -m trading_system` delegates to the composition root. It does not construct individual services itself.

If the current installation still has unresolved composition gaps, the entrypoint reports those gaps and exits without starting the runtime.

## Acceptance criteria

1. One authoritative assembly operation exists.
2. The operation returns `RuntimeControl` when all required dependencies are supplied.
3. RuntimeControl owns lifecycle semantics.
4. RuntimeScheduler remains downstream of RuntimeControl.
5. ObservationLifecycleCoordinator remains the observation-boundary authority.
6. ObservationRunner remains the one-observation orchestration authority.
7. Existing deterministic strategy/risk/governance/decision/execution components are reused.
8. No production stub is introduced for a missing business component.
9. Composition tests verify the real object graph.
10. The full baseline test suite remains green.
