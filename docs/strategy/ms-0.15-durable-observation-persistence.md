# MS-0.15 — Durable Observation Persistence

**Status:** Canonical / frozen  
**Milestone:** MS-0.15  
**Scope:** Durable persistence for the frozen MS-0.14 observation contract.

## Purpose

MS-0.15 introduces durable storage for ObservationRevision records without changing observation semantics.

The MS-0.14 observation contract remains authoritative for:
- observation identity;
- completed-H1 anchoring;
- append-only revisions;
- terminal-state reuse;
- retryable WAIT;
- revision-conflict recovery;
- ObservationExecutionError as the unexpected application failure boundary.

MS-0.15 adds only persistence semantics.

## DP-01 — Durable storage technology

**Locked: SQLite.**

The application depends on ObservationRepositoryPort. SQLite is an adapter implementation detail.

No SQLite connection, cursor, SQL statement, transaction object, or SQLite-specific type crosses the domain/application boundary.

## DP-02 — Durable observation schema

**Locked: hybrid relational envelope + canonical JSON snapshot.**

Table: observation_revisions

Columns:
- observation_id
- instrument
- h1_boundary_timestamp
- revision_number
- status
- reason
- evaluation_timestamp
- snapshot_json
- schema_version

The relational envelope provides durable identity, revision, status, reason, timestamps, schema version, and indexes.

snapshot_json preserves the complete canonical ObservationRevision. It is not replaced by a second relational domain representation.

## DP-03 — Identity and revision constraints

Observation identity is (instrument, h1_boundary_timestamp).

The durable row identity is (instrument, h1_boundary_timestamp, revision_number).

The database enforces UNIQUE(instrument, h1_boundary_timestamp, revision_number) and revision_number >= 1.

The observation identity itself is not unique because multiple revisions are required.

The highest revision number for an observation identity is the durable current revision.

## DP-04 — Transaction and concurrency semantics

Revision append is an atomic SQLite transaction.

The repository must not implement an unprotected read-then-write sequence for revision allocation.

A uniqueness conflict on the durable revision key is an expected concurrency event:

revision conflict → read canonical latest revision → return latest revision

The losing concurrent operation must not create a second row with the same identity and revision.

SQLite transaction/locking mechanics remain entirely inside SQLiteObservationRepository.

## DP-05 — Repository failure semantics

Repository failures are infrastructure failures, not observation outcomes.

They must not be converted into WAIT or NO_SETUP.

Infrastructure failures include database unavailable, unrecoverable database locking, serialization/deserialization failure, schema mismatch, I/O failure, migration failure, and unexpected SQL errors.

These propagate through the repository/application boundary and participate in the existing ObservationExecutionError boundary.

A revision conflict is the explicit exception: it is an expected concurrency event and is recovered by reading the canonical latest revision.

## DP-06 — Migration and versioning strategy

SQLite schema migrations are explicit, numbered, forward-only, deterministic, and durably recorded as applied.

Database schema versioning is distinct from the observation snapshot's schema_version.

Example: database migration 001_initial_observation_revisions; observation schema MS-0.14.

Migrations must preserve historical observations and must not silently rewrite their historical meaning.

Application startup must not silently operate against an incompatible database schema.

Destructive historical rewriting is outside MS-0.15.

## Repository contract

The existing application port remains the boundary:

latest(identity) -> ObservationResult | None
append(revision) -> ObservationResult

The durable adapter implements this contract.

## Canonical persistence invariants

1. Every persisted revision has revision_number >= 1.
2. Every persisted revision is immutable after append.
3. The same (instrument, h1_boundary_timestamp, revision_number) cannot be persisted twice.
4. latest(identity) returns the highest revision number.
5. The persisted snapshot reconstructs the same canonical ObservationRevision.
6. Terminal revisions remain terminal and are returned without re-evaluation.
7. Revision conflicts are recoverable concurrency events.
8. Infrastructure failures remain infrastructure failures.
9. Domain/application contracts contain no SQLite dependencies.
10. Historical snapshots remain reconstructable after future application versions.

## Out of scope

MS-0.15 does not introduce new observation states, strategy rules, risk rules, governance rules, broker/MT5 persistence, live execution persistence, destructive migrations, schema rewriting of historical observations, or arbitrary retry policies beyond explicit revision-conflict recovery.