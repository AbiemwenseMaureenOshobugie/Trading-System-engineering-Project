# MS-0.17 — Operational Control

## Purpose

MS-0.17 defines ASTER's runtime operational-control boundary. It wraps the
existing MS-0.16 observation lifecycle coordinator without changing observation
methodology, freshness semantics, polling policy, or trading logic.

## Frozen decisions

### OP-D01 — Runtime lifecycle

The runtime lifecycle is externally controlled:

`STOPPED → STARTING → RUNNING → STOPPING → STOPPED`

Runtime control exposes `start()` and `stop()`.

Starting does not create a scheduler, retry policy, polling policy, or new
observation methodology. The existing observation coordinator remains
responsible for deciding whether an observation opportunity exists.

Stopping prevents new runtime-driven observation invocations and waits for any
currently in-flight invocation to reach its safe boundary before ownership is
released and the runtime becomes STOPPED.

Runtime lifecycle is separate from ObservationStatus.

### OP-D02 — Manual invocation

Manual invocation follows:

`Operator → RuntimeControl → ObservationLifecycleCoordinator.invoke_manual() → ObservationRunner.run()`

Runtime control never bypasses the coordinator.

Manual invocation does not force an observation through lifecycle checks; the
existing coordinator and repository semantics remain authoritative.

### OP-D03 — Single-instance ownership

One OS/process-level exclusive ownership lock exists for each ASTER
`runtime_id`.

At most one active runtime coordinator may own that identity.

Ownership failure is a runtime start failure, not an observation WAIT outcome.

No distributed lease, leader election, retry, failover, or recovery protocol is
introduced.

### OP-D04 — Runtime status

Runtime status is a dedicated operational model:

- `STOPPED`
- `STARTING`
- `RUNNING`
- `STOPPING`
- `FAILED`

These states are not added to ObservationStatus, DecisionStatus, RiskStatus,
GovernanceStatus, or execution state.

### OP-D05 — Runtime failure visibility

Runtime failures use a dedicated structured representation containing:

- `failure_id`
- `runtime_id`
- `timestamp`
- `component`
- `failure_code`
- `message`
- `reference`

Infrastructure failures are never translated into trading outcomes.

### OP-D06 — Runtime configuration

Runtime configuration is explicit and separated into:

1. instrument configuration;
2. operational time configuration;
3. data-provider configuration;
4. persistence configuration.

Configuration does not contain methodology, risk, governance, entry, stop-loss,
target, or trade-limit rules.

### OP-D07 — Operational audit

Runtime control emits dedicated operational audit events, separate from
strategy/trading audit.

The initial canonical events are:

- `RUNTIME_START_REQUESTED`
- `RUNTIME_STARTED`
- `RUNTIME_START_FAILED`
- `RUNTIME_STOP_REQUESTED`
- `RUNTIME_STOPPED`
- `RUNTIME_FAILURE`
- `RUNTIME_OWNERSHIP_ACQUIRED`
- `RUNTIME_OWNERSHIP_REJECTED`
- `MANUAL_OBSERVATION_REQUESTED`
- `MANUAL_OBSERVATION_COMPLETED`
- `MANUAL_OBSERVATION_FAILED`

Operational audit records evidence only. It cannot authorize or modify trading
decisions.

## Explicit exclusions

MS-0.17 introduces no:

- new observation states;
- retry/backoff;
- second scheduler;
- polling-policy redesign;
- AI;
- methodology changes;
- freshness redesign;
- live execution;
- Strategy → Risk → Governance → Decision → Execution changes.

## Runtime invariant

`RUNNING` means the runtime owns its identity and accepts runtime/manual
control. It does not mean that a setup exists, that a decision is VALID, or
that execution is authorized.
