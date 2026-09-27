# MS-0.14 — H1-Anchored Deterministic Observation Runner

## Status

**Contract frozen.** OR-07 through OR-28 are implemented as the MS-0.14 observation contract.

MS-0.14 is an orchestration milestone. It introduces no new trading methodology.

## OR-07 — Observation scope

The Observation Runner orchestrates the existing deterministic ASTER pipeline:

Twelve Data → MarketDataPort → Observation Runner → canonical completed MarketCandle → H1 Market Structure → Key-Level Detection → M15 Confirmation → Setup Classification → Risk → Governance → Decision → Observation Result.

The runner does not reinterpret strategy rules.

## OR-08 — Observation clock

Each observation is anchored to one completed H1 boundary. M15 is confirmation data inside that H1 observation and does not create independent observation cycles.

## OR-09 — History

The runner receives an operational history window from an injected history resolver. No fixed candle count is introduced by MS-0.14. The resolver is responsible for requesting enough history for the installed deterministic engines.

## OR-10 — Insufficient history

If the supplied quality metadata says the required history is insufficient, the runner persists WAIT / INSUFFICIENT_HISTORY. No downstream methodology result is fabricated.

## OR-11 — Invalid market data

If provider validation reports invalid/rejected market data, the runner persists WAIT / INVALID_MARKET_DATA. The runner never repairs, interpolates, forward-fills, or invents market data.

## OR-12 — Incomplete market data

If the required data window is structurally incomplete, the runner persists WAIT / INCOMPLETE_MARKET_DATA. Deterministic engines are not run on incomplete data.

## OR-13 — No new H1 boundary

If no completed H1 boundary exists, the runner returns a transient NO_OBSERVATION / NO_NEW_H1_CANDLE result. No observation identity is persisted.

## OR-14 — No qualifying setup

A successfully evaluated observation with no candidates persists NO_SETUP / NO_QUALIFYING_SETUP.

## OR-15 — Multiple candidates

All qualifying DecisionCandidates are retained in the same H1 observation. The runner never ranks or selects a winner.

## OR-16 — Candidate-local qualification

Risk, Governance, and Decision run independently for each candidate. One candidate cannot alter another candidate's result.

## OR-17 — Observation-level status

Observation status answers whether the observation itself was evaluable:

- WAIT
- NO_SETUP
- EVALUATED
- NO_OBSERVATION

Candidate outcomes retain Risk/Governance/Decision statuses separately.

## OR-18 / OR-19 — Idempotency and identity

The identity is instrument + completed H1 boundary timestamp. EVALUATED and NO_SETUP are terminal for that identity. WAIT is retryable.

## OR-20 — Full snapshot

Each revision preserves identity, revision number, evaluation time, methodology versions, H1/M15 data references, validation outcome, H1 structure, Key Levels, all candidates, all downstream candidate outcomes, and provenance references.

## OR-21 — Persistence

ObservationRepositoryPort is the canonical persistence boundary. The reference adapter is concurrency-safe in-memory and is intentionally replaceable by a durable implementation.

## OR-22 — WAIT retry

A later invocation for the same identity may append a new revision after a WAIT result. Terminal results are reused.

## OR-23 — Concurrent invocation

Repository uniqueness is observation identity + revision number. A concurrent insert conflict is resolved by reading the canonical latest revision.

## OR-24 / OR-25 — Append-only revisions

Each evaluation attempt is immutable. The highest revision number is the current state.

## OR-26 — Reproducibility

Revisions carry methodology versions, deterministic H1/M15 data references, validation outcomes, pipeline outputs, and provenance references.

## OR-27 / OR-28 — Application failure

Unexpected deterministic-component or persistence failures are not ordinary observation outcomes. ObservationRunner raises ObservationExecutionError.

## Boundary

MS-0.14 owns orchestration, observation identity, revisioning, persistence interaction, and observation-level status.

It does not own H1 methodology, Key-Level rules, governing-Key-Level selection semantics, M15 confirmation rules, Setup Classification semantics, Risk, Governance, Decision, execution authorization, or provider repair.
