# MS-0.27 — Production Deployment Contract

## Purpose

MS-0.27 defines ASTER's production deployment and operational contract across
the staged operating modes:

1. Decision-support
2. Paper trading
3. MT5 demo
4. Controlled live

MS-0.27 does not introduce new strategy, confirmation, risk, governance,
broker, or market-microstructure rules. It defines the deployment, runtime,
persistence, dependency, observability, failure, recovery, and rollback
boundaries required to operate those modes safely.

The decisions in this document are the provisional MS-0.27 contract decisions
from the bounded PD-01 through PD-10 audit. This document is the canonical
specification that makes those decisions implementation authority.

## PD-01 — Production Definition

ASTER production means a deployment contract capable of supporting all staged
operational modes, with controlled live as the eventual highest-risk mode.

Production is therefore not synonymous with live trading.

The deployment contract must explicitly support:

- Decision-support
- Paper trading
- MT5 demo
- Controlled live

A deployment must not make a higher-risk mode executable merely because the
software is running.

Operational authority remains:

Configuration → Governance → Decision → Execution

Deployment capability does not equal execution authorization.

Live broker credentials are not required for lower-risk modes.

## PD-02 — Runtime Lifecycle

The canonical runtime lifecycle is:

```
STARTING
   ↓
INITIALIZING
   ↓
RUNNING
   ↓
DEGRADED
   ↓
RECOVERING
   ↓
RUNNING
   ↓
SHUTTING_DOWN
   ↓
STOPPED
```

The `DEGRADED` ↔ `RECOVERING` path is a recovery path; recovery may return
to `RUNNING` only after the required readiness conditions are re-established.

### Runtime states

- **STARTING** — the process has started but runtime readiness has not been
  established.
- **INITIALIZING** — configuration, dependencies, persisted state, and required
  components are being validated.
- **RUNNING** — required dependencies and internal invariants are healthy for
  the current operating mode.
- **DEGRADED** — the process remains alive but one or more required
  capabilities are unavailable or no longer healthy.
- **RECOVERING** — deterministic recovery is being attempted.
- **SHUTTING_DOWN** — new work is refused while required safe-shutdown
  persistence and reconciliation work is completed.
- **STOPPED** — no operational activity is permitted.

DEGRADED does not mean that ASTER may continue trading normally. The applicable
safe-state policy determines which capabilities remain available.

## PD-03 — Configuration and Secrets

Configuration and secrets are separate concerns.

### Configuration

Non-secret deployment configuration may include:

- operating mode
- instruments
- environment identity
- service endpoints
- non-secret operational parameters
- logging and observability configuration

### Secrets

Secrets include:

- broker credentials
- API keys
- tokens
- passwords
- private credentials

### Rules

1. Secrets must never be committed to source control.
2. Secrets must never be embedded in application code.
3. Secrets must not appear in normal application logs.
4. Secrets must not appear in audit payloads.
5. Configuration must be externally supplied to the deployment.
6. Production credentials must be separated from development/demo credentials.
7. Missing required secrets must prevent the dependent capability from becoming
   ready.
8. A deployment must not silently substitute credentials from another
   environment.

For the first deployment implementation, environment-provided
configuration/secrets are the baseline.

No cloud secret-management product is mandated by MS-0.27.

## PD-04 — Persistence and Recovery

ASTER must distinguish authoritative state from derived state.

### Authoritative state

Material operational facts include:

- decisions
- execution/order state
- fills
- journal/audit events
- relevant configuration/version identity

Derived state may be reconstructed from authoritative records.

### Recovery invariant

On restart:

```
Persisted state
      ↓
Validation
      ↓
Recovery
      ↓
Runtime readiness
```

ASTER must not assume that in-memory state survives restart.

Audit/event history must be durable.

Execution state must remain explicit and must not be reconstructed ambiguously.
The canonical states remain distinguishable:

- AUTHORIZED
- SUBMITTED
- FILLED
- FAILED

Recovery must be idempotent.

### Duplicate-instance prevention

There must be one authoritative active runtime per trading scope.

Two production instances must not independently believe that they are
authorized to execute the same trading scope.

The initial implementation may use a simple deterministic runtime/instance
lock mechanism. A distributed coordination system is not mandated at this
stage.

Backups are required for durable operational records. Exact storage and backup
technology remain implementation decisions.

## PD-05 — External Dependency Health

External dependencies are explicit runtime capabilities rather than assumed
infrastructure.

Relevant dependencies include:

- market data
- broker/MT5 when required by the active mode
- persistence
- configuration/secrets
- audit/event storage

ASTER must distinguish:

- **AVAILABLE**
- **DEGRADED**
- **UNAVAILABLE**
- **STALE**

### Market data

Stale data must never be treated as current market data.

If required market data becomes unavailable or stale:

**new strategy decisions must be blocked.**

Existing execution state must not be fabricated, rewritten, or altered merely
because the market-data source disappeared.

### Broker / MT5

If the active mode does not require broker connectivity, broker failure must
not make the entire system unhealthy.

If the active mode requires broker connectivity:

```
broker unavailable
      ↓
execution capability unavailable
      ↓
new execution blocked
```

No strategy bypass is permitted.

## PD-06 — Observability

ASTER has four distinct observability layers.

### 1. Application logs

Application logs support operational diagnostics, including:

- startup and shutdown
- configuration validation
- dependency failures
- exceptions
- recovery attempts

Logs are not the authoritative historical record.

### 2. Audit events

Audit events provide authoritative system history for material events such as:

- decisions
- authorization
- execution transitions
- failures
- material state changes

Audit events are not merely log messages.

### 3. Health and readiness

At minimum, the deployment exposes distinct concepts for:

- liveness
- readiness
- dependency health

A process being alive does not imply that it is ready to make decisions or
execute.

### 4. Metrics

Metrics are justified only when they answer operational questions.

Initial useful metrics may include:

- decision counts by outcome
- execution counts by state
- dependency failures
- stale-data occurrences
- recovery attempts
- recovery failures

MS-0.27 does not require a large monitoring stack.

### Alerting

Operationally significant failures require alerting.

The alerting platform is deferred as an implementation decision.

## PD-07 — Deployment Artifact

MS-0.27 is deployment-platform neutral.

Docker is not mandatory.

Kubernetes is not required.

ASTER must first be deployable as a deterministic application/package/process
that satisfies this contract.

Optional containerization may later be adopted if it materially improves:

- reproducibility
- isolation
- deployment consistency
- operational management

The deployment relationship is:

```
Application/package
       ↓
Deployment contract
       ↓
Optional containerization
       ↓
Optional orchestration
```

Infrastructure technology serves the deployment contract; it does not define
the contract.

## PD-08 — Failure and Safe-Shutdown Policy

ASTER fails closed for new execution.

If the system cannot establish the information, state, authorization, or
dependency condition required for safe execution:

> **Do not execute.**

### Authorized but unsubmitted

If:

- Decision = VALID
- Risk = RISK_AUTHORIZED
- Governance = GOVERNANCE_AUTHORIZED
- Execution = AUTHORIZED

but no order has been submitted before shutdown or failure, the authorization
expires with the runtime context.

It must not automatically be submitted after restart.

A new evaluation is required.

### Submitted but unfilled

SUBMITTED is a distinct recoverable state.

ASTER must preserve SUBMITTED and reconcile it rather than assuming that it
failed.

For broker/MT5 execution, reconciliation with the external execution system
will eventually be required.

### Filled

A persisted FILLED state remains a fill.

Restart must never reinterpret a fill as merely AUTHORIZED or SUBMITTED.

### Failed

FAILED is an explicit terminal execution state. Recovery must preserve the fact
that the execution failed rather than silently converting it into another
state.

### Duplicate execution

Execution/order identity must be stable enough that a retry cannot blindly
create a second execution for the same authorized decision.

### Safe shutdown

During SHUTTING_DOWN:

- no new strategy decisions that could initiate execution
- no new execution submissions
- material state is persisted
- audit events are persisted
- recoverable execution state remains explicit
- termination occurs only after required shutdown persistence completes

## PD-09 — Rollback and Operational Recovery

Application deployment and configuration are versioned independently.

ASTER must be able to identify:

- application version
- strategy version
- configuration version
- relevant execution/deployment state

### Deployment rollback

A failed deployment may return to a previously validated application version.

### Configuration rollback

Configuration changes must be version-identifiable and reversible.

### Strategy safety

Application rollback must not silently rewrite historical decisions or
executions.

Historical records remain immutable.

### Recovery scope

Operational recovery must cover:

1. process restart
2. dependency recovery
3. persistence recovery
4. execution-state reconciliation
5. return to readiness

Backup technology, deployment platform, and operational tooling remain
implementation-level decisions.

## PD-10 — Canonical Contract

MS-0.27 establishes the following canonical deployment contract.

### Production definition

ASTER can be deployed across all staged operational modes, with controlled
live as the eventual highest-risk mode.

### Runtime

```
STARTING
→ INITIALIZING
→ RUNNING
↔ DEGRADED
→ RECOVERING
→ RUNNING
→ SHUTTING_DOWN
→ STOPPED
```

The recovery transition is conditional: RECOVERING returns to RUNNING only
after required readiness conditions are restored.

### Configuration

Configuration and secrets are separate.

Secrets are externally supplied and are never stored in source control,
application code, normal logs, or audit payloads.

### Persistence

Material decisions, execution state, fills, and audit history are durable and
recoverable.

### External dependencies

Required dependencies must be healthy and current before their dependent
capability is considered ready.

### Observability

Application logs, audit events, health/readiness, dependency health, and
justified metrics are separate concerns.

### Deployment

The deployment contract is platform-neutral.

Docker and Kubernetes are not mandatory.

### Failure

New execution fails closed whenever required authorization, state, data, or
dependency conditions cannot be established.

### Recovery

Execution state is reconciled rather than guessed.

### Rollback

Application, configuration, strategy, and relevant deployment identities are
version-identifiable, while historical records remain immutable.

## Explicit Non-Decisions

MS-0.27 intentionally does not mandate:

- Docker
- Kubernetes
- a cloud provider
- a cloud secret-management product
- a broker/MT5 implementation
- a monitoring vendor or monitoring stack
- a distributed coordination system
- a specific persistence technology
- a specific backup technology
- a specific deployment platform

These remain implementation or later infrastructure decisions.

## Acceptance Criteria

1. The four staged operating modes are representable without equating
   deployment capability with execution authorization.
2. Runtime state is distinguishable across STARTING, INITIALIZING, RUNNING,
   DEGRADED, RECOVERING, SHUTTING_DOWN, and STOPPED.
3. DEGRADED cannot be interpreted as permission to continue trading normally.
4. Configuration and secrets remain separate.
5. Required secrets are externally supplied and cannot silently fall back to
   another environment.
6. Authoritative operational state is distinguishable from derived state.
7. Durable execution state preserves AUTHORIZED, SUBMITTED, FILLED, and FAILED.
8. Recovery is idempotent and duplicate execution is prevented.
9. One authoritative active runtime exists per trading scope.
10. Required external dependencies expose explicit health/currency state.
11. Required stale or unavailable market data blocks new strategy decisions.
12. Required broker/MT5 unavailability blocks new execution when that dependency
    is required by the active mode.
13. Logs, audit events, health/readiness, and metrics remain distinct.
14. Operationally significant failures are alertable without mandating a vendor.
15. The deployment artifact remains platform-neutral.
16. New execution fails closed when safe authorization or dependency conditions
    cannot be established.
17. AUTHORIZED but unsubmitted work expires with the runtime context.
18. SUBMITTED state is preserved and reconciled rather than guessed.
19. FILLED state remains immutable across restart.
20. Application and configuration versions are independently identifiable.
21. Rollback does not rewrite historical decisions or executions.
22. No MS-0.27 rule duplicates strategy, risk, governance, broker, or
    market-microstructure logic.
