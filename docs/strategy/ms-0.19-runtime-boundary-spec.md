# MS-0.19 — Runtime Boundary Resolution

RHD-01, RHD-02, and RHD-03 are locked.

MS-0.19 closes the runtime boundary contract gap identified after MS-0.18. It introduces no new scheduler or observation authority.

## RHD-01 — Boundary Calculation API

ObservationLifecycleCoordinator exposes:

    def next_invocation_at(*, instrument: str, now: datetime) -> datetime | None: ...

The coordinator delegates to the existing observation boundary authority, obtains the next completed H1 boundary, adds the existing operational poll offset, and returns that timestamp. None means no boundary is currently schedulable.

RuntimeControl delegates to the coordinator. RuntimeScheduler consumes the returned timestamp and performs no H1 or operational-boundary mathematics.

## RHD-02 — Runtime Integration Test

MS-0.19 includes a real runtime integration test covering RuntimeScheduler → RuntimeControl → ObservationLifecycleCoordinator → ObservationRunner → Strategy → Risk → Governance → Decision → ObservationRevision.

The coordinator is real, the observation-processing path is real, and the resulting observation revision reaches the repository boundary. The test also verifies scheduled/manual convergence for the same observation identity.

## RHD-03 — Scheduler Boundary-Failure Isolation

Boundary-calculation exceptions use the existing RuntimeControl runtime-failure boundary. The failure is recorded with the existing coordinator failure component and failure code BOUNDARY_CALCULATION_FAILED. Runtime remains RUNNING.

The failure is not converted into WAIT, NO_SETUP, EVALUATED, or an observation FAILED state. No new failure taxonomy is introduced.

## Authority boundaries

| Layer | Authority |
|---|---|
| RuntimeScheduler | When to invoke RuntimeControl |
| RuntimeControl | Runtime lifecycle and runtime failure boundary |
| ObservationLifecycleCoordinator | Next observation invocation boundary and observation identity |
| ObservationRunner | One observation-processing path |
| Strategy / Risk / Governance / Decision | Trading outcome semantics |
| Execution / Broker / MT5 | Execution authority |

## Explicit exclusions

No trading rules, strategy changes, risk changes, governance changes, decision changes, execution mechanism, broker/MT5 integration, AI/ML authority, new failure taxonomy, scheduler-side boundary calculation, second scheduling authority, retry/backoff policy, or catch-up/replay queue.

## Invariant

Manual and scheduled invocation converge on the same observation identity and durable revision semantics. The scheduler never becomes an observation-processing authority.
