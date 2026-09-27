# MS-0.16 — Observation Lifecycle Coordination

## Status
**Contract frozen.**

MS-0.16 introduces one operational component: the Observation Lifecycle Coordinator. It coordinates invocation opportunities around the existing MS-0.13 H1 boundary contract and delegates one observation to the existing MS-0.14 ObservationRunner.

MS-0.16 introduces no new observation state and no new trading methodology.

## OL-01 — Invocation authority
The Observation Lifecycle Coordinator is the only component responsible for deciding that an observation invocation opportunity has arrived.

Operational Clock → Observation Lifecycle Coordinator → ObservationRunner

The Coordinator does not perform observation logic. ObservationRunner remains responsible for one observation invocation and its existing MS-0.14 semantics.

## OL-02 — Invocation cadence
Invocation is boundary-driven using the existing MS-0.13 contract.

For an instrument, the Coordinator:
1. determines the newest completed H1 boundary using the existing boundary semantics;
2. calculates the operational invocation opportunity as the completed H1 boundary plus the existing 30-second post-boundary offset;
3. invokes ObservationRunner when that opportunity has arrived;
4. supports an explicit/manual invocation path for testing and operational recovery.

The 30-second offset is operational configuration, not a trading rule. MS-0.16 does not introduce a new polling interval.

## OL-03 — Freshness/currentness
Freshness is H1-boundary and observation-identity based.

Canonical observation identity: (instrument, h1_boundary_timestamp)

Currentness is determined from the durable latest revision for that identity.

| Durable state | Coordinator behavior |
|---|---|
| EVALUATED | Do not re-evaluate that identity |
| NO_SETUP | Do not re-evaluate that identity |
| WAIT | Permit another invocation |
| No persisted identity | Evaluate it |
| New H1 boundary | Evaluate the new identity |

Elapsed-time freshness is not used. The Coordinator must not introduce "fresh for N seconds", "last run within N minutes", or "run every N minutes" rules.

## OL-04 — Operational failure handling
Operational and infrastructure failures remain failures. They are never converted into observation outcomes.

Existing observation outcomes remain authoritative: WAIT, NO_SETUP, EVALUATED, NO_OBSERVATION.

Provider/infrastructure failure, persistence failure, and unexpected runner/component failure remain operational or infrastructure failures under their existing boundaries.

The Coordinator does not introduce RECOVERING, RETRYING, FAILED, or any other observation status. It does not introduce retry counters, exponential backoff, arbitrary retry delays, or a new retry policy.

After an operational failure, a later invocation opportunity may attempt the same observation identity again according to existing durable state and runner semantics.

## OL-05 — Restart/recovery
Recovery is derived from durable observation state.

On startup or explicit recovery:
1. load the latest durable observation for the relevant instrument/boundary;
2. determine the latest completed H1 boundary;
3. compare it with the durable observation identity;
4. reuse terminal observations;
5. permit WAIT observations to be retried;
6. evaluate a newer H1 identity.

No recovery record is required.

A terminal revision remains terminal and is reused. A WAIT revision remains retryable. A newer boundary produces a new observation identity and is evaluated by the existing runner.

## Manual invocation
The Coordinator exposes an explicit/manual invocation path for testing and operational recovery.

Manual invocation delegates to ObservationRunner and does not bypass its identity, terminal-state, revision, or failure semantics.

## Boundary ownership
| Concern | Owner |
|---|---|
| When to invoke | MS-0.16 Coordinator |
| H1 boundary semantics | MS-0.13 / existing boundary component |
| Observation identity | MS-0.14 |
| Observation evaluation | MS-0.14 ObservationRunner |
| WAIT / NO_SETUP / EVALUATED | MS-0.14 |
| Terminal reuse | MS-0.14 + Repository |
| Revision creation | MS-0.14 |
| Durable revision storage | MS-0.15 |
| Revision conflict recovery | MS-0.15 / Runner boundary |
| Restart recovery | MS-0.16 using existing durable semantics |
| Trading methodology | Existing strategy milestones |
| Risk | MS-0.4 |
| Governance | MS-0.5 |
| Decision | MS-0.6 |
| Execution | MS-0.7 |
| AI/ML | Not involved |

## Explicit non-goals
MS-0.16 does not introduce RECOVERING, RETRYING, a failed observation status, retry counters, exponential backoff, arbitrary retry intervals, duplicate freshness rules, new H1 logic, new M15 logic, scheduler-owned strategy decisions, AI involvement, trade prioritization, or persistence redesign.

## Acceptance criteria
1. Only the Coordinator decides whether a scheduled observation opportunity has arrived.
2. The Coordinator delegates observation evaluation to ObservationRunner.
3. Scheduled invocation is derived from the existing completed-H1 boundary plus the existing 30-second operational offset.
4. Manual invocation is available.
5. Terminal durable identities are not re-evaluated.
6. WAIT identities remain retryable.
7. New H1 boundaries create new observation identities.
8. No elapsed-time freshness rule exists.
9. No new observation state exists.
10. Operational failures remain failures.
11. No retry policy is introduced.
12. Restart recovery is derived from durable observation state.
