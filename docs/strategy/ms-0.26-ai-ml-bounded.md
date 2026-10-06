# MS-0.26 — AI/ML Bounded Assistance Contract

## Status

**Frozen — advisory, non-authoritative AI/ML.**

MS-0.26 defines the authority, input, output, provenance, persistence, identity, retry, and normalization boundaries for AI/ML assistance in ASTER.

It does not introduce a model provider, prompt framework, prediction strategy, trading rule, risk rule, governance rule, execution authority, or production deployment mechanism.

## 1. Authority

AI/ML is strictly advisory.

AI/ML may assist:

- interpretation;
- explanation;
- research;
- journaling;
- analytics;
- later separately validated enhancements.

AI/ML must not:

- create or modify a valid trading setup;
- alter Strategy qualification;
- authorize Risk;
- authorize Governance;
- authorize Execution;
- change SL/TP;
- change position sizing;
- alter session eligibility;
- mutate authoritative Decision state.

ASTER must remain operationally correct when AI/ML is unavailable.

## 2. Inputs

AI/ML may consume canonical market data and deterministic ASTER state, including:

- validated/normalized market data;
- H1/M15 structure;
- Key Levels;
- confirmation/setup information;
- Risk/Governance/Decision outputs;
- execution and journal history.

AI/ML receives references to authoritative state rather than owning or replacing that state.

## 3. Output

AI/ML returns a structured, explicitly non-authoritative observation.

AI output must never become authoritative Strategy, Risk, Governance, Decision, or Execution state.

AI-generated values for SL, TP, position size, risk percentage, session eligibility, or execution authorization are advisory text/observations only and cannot control those fields.

## 4. Bounded consumers

AI observations may flow only to explicitly bounded consumers:

- `EXPLANATION`
- `RESEARCH`
- `JOURNAL`
- `ANALYTICS`

No AI observation may flow into Strategy, Risk, Governance, Decision, or Execution as an authority-bearing input.

## 5. Canonical observation

Every AI invocation produces one immutable `AIObservation` record.

The record contains:

- `observation_id`
- `status`
- `model_id`
- `model_version`
- `requested_at`
- `completed_at`
- `consumer`
- `input_references`
- `aster_state_references`
- `context_fingerprint`
- `observations`
- `confidence`
- `explanation`
- `limitations`
- `failure_category`
- `schema_version`

`decision_id` is not a mandatory dedicated field. When relevant, it is represented through `aster_state_references`.

## 6. Status

The canonical AI lifecycle statuses are:

- `COMPLETED`
- `UNAVAILABLE`
- `TIMEOUT`
- `FAILED`
- `INVALID_OUTPUT`

These are AI lifecycle states, not trading states.

AI failure must never become `WAIT`, `NO_SETUP`, `RISK_REJECTED`, or `GOVERNANCE_BLOCKED`.

## 7. Consumer identity

The consumer is one of the four bounded consumers above. Consumer identity grants no additional authority.

## 8. Provenance

AI observations preserve:

- model identity/version;
- request and completion timestamps;
- input references;
- authoritative ASTER-state references;
- context fingerprint;
- consumer;
- schema version.

Resolved credentials, secrets, API keys, or secret-bearing prompt material must not enter the observation record.

## 9. Context identity

`context_fingerprint` identifies the canonical input context supplied to an invocation.

The fingerprint does not deduplicate observations.

Two invocations with identical context have different `observation_id` values and may share the same context fingerprint.

## 10. Retry semantics

A retry is a new AI invocation and therefore creates a new immutable `AIObservation`.

A failed observation is never mutated into a successful observation.

## 11. Output normalization

AI adapters normalize provider/model responses into the canonical `AIObservation` contract before the result enters ASTER.

Malformed or contract-invalid output becomes `INVALID_OUTPUT`.

Provider-specific response structures do not enter the domain contract.

## 12. Persistence

AI observations are durable append-only records.

Persistence follows the established ASTER pattern:

```
AIObservation
    ↓
AIObservationRepositoryPort
    ↓
SQLite adapter
    ↓
SQLite
```

The persistence adapter may use a relational envelope plus canonical JSON snapshot.

AI observation persistence does not reuse market-observation revision semantics; it is a separate domain record.

## 13. Explicit non-goals

MS-0.26 does not introduce:

- AI trading signals;
- predictive buy/sell models;
- automated model selection;
- model training pipelines;
- provider credentials;
- prompt storage;
- broker execution through AI;
- AI-controlled risk;
- AI-controlled governance;
- AI-controlled strategy;
- AI-controlled session policy;
- production deployment;
- cloud infrastructure;
- model serving infrastructure.

## 14. Architectural invariant

**The trading system governs the AI. The AI does not own the trading system.**

ASTER must operate correctly with the AI layer completely absent.
