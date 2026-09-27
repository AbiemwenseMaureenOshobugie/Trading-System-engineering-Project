# MS-0.18 — Runtime Scheduler / Observation Invocation

## Purpose

MS-0.18 adds one owned long-running runtime scheduler between RuntimeControl and the frozen MS-0.16 observation lifecycle coordinator.

It answers only: When should RuntimeControl.run_if_due() be invoked?

It adds no trading methodology and no new observation authority.

## Frozen decisions

### SC-D01 — Scheduler execution model
One RuntimeScheduler instance is owned by one running RuntimeControl. The scheduler waits for the next operational boundary, evaluates configured instruments, invokes them sequentially, and repeats while the runtime is running. The scheduler does not own observation logic.

### SC-D02 — Calculation of the next H1 boundary
The scheduler delegates boundary calculation to the existing MS-0.13/MS-0.16 boundary authority through the observation coordinator. The existing completed-H1 boundary and 30-second operational offset remain the authority. The scheduler does not implement a polling interval or duplicate H1 boundary mathematics.

### SC-D03 — Multiple instruments
RuntimeConfig.instruments supplies the configured instrument order. At each scheduling opportunity, instruments are evaluated sequentially in that deterministic configuration order. The scheduler does not rank, suppress, or prioritize instruments.

### SC-D04 — Invocation overrun
There is no backlog or catch-up queue. After an invocation completes, the scheduler asks the boundary authority for the current/latest operational opportunity. A missed historical boundary is not replayed. Observation identity and duplicate prevention remain the coordinator's responsibility.

### SC-D05 — Scheduler failure handling and audit
Each instrument invocation is isolated. If RuntimeControl.run_if_due() raises for one instrument, the scheduler continues with the remaining configured instruments. The scheduler creates no new failure taxonomy and performs no retry. RuntimeControl remains the existing failure/audit boundary.

An observation invocation failure is recorded as a structured RuntimeFailure without changing a healthy RUNNING runtime into a terminal FAILED state. Start/ownership failures may still transition the runtime to FAILED according to MS-0.17.

A later legitimate operational boundary creates the next invocation opportunity through normal coordinator semantics.

### SC-D06 — Scheduler start/stop integration
RuntimeControl owns scheduler lifecycle.

start(): acquire runtime ownership, transition to RUNNING, then start exactly one scheduler. If ownership acquisition fails, the scheduler does not start.

stop(): transition to STOPPING, signal the scheduler to stop, wait for the scheduler thread to terminate, wait for any in-flight runtime invocation to finish, release runtime ownership, then transition to STOPPED.

No new scheduled invocation begins after stop enters STOPPING.

## Authority boundaries

| Layer | Authority |
|---|---|
| MS-0.18 RuntimeScheduler | When to invoke runtime control |
| MS-0.17 RuntimeControl | Runtime ownership/lifecycle and invocation failure boundary |
| MS-0.16 ObservationLifecycleCoordinator | Whether an observation opportunity is due and observation identity |
| MS-0.14 ObservationRunner | How one observation is evaluated |
| Strategy / Risk / Governance / Decision / Execution | Trading outcome authority |

## Explicit exclusions

MS-0.18 introduces no cron/external scheduler, second scheduling authority, task queue, distributed scheduler, retry/backoff policy, catch-up/replay queue, trading methodology, strategy changes, risk changes, governance changes, session-policy changes, AI/ML authority, or execution authority.

## SC-D05 integration adjustment

MS-0.17 originally treated an observation invocation exception as a terminal runtime FAILED state. That conflicts with SC-D05 because one instrument failure must not terminate scheduling for the other instruments.

MS-0.18 therefore distinguishes runtime-start/ownership failure, which remains a terminal FAILED runtime state, from instrument observation invocation failure while RUNNING, which records RuntimeFailure and operational audit evidence while the runtime remains RUNNING.

This is an integration correction to the existing runtime-control boundary, not a new observation or trading rule.

## Runtime invariant

RUNNING means the runtime owns its identity, the scheduler may operate, and manual/runtime control is accepted. It does not imply that an observation, setup, decision, or execution exists.
