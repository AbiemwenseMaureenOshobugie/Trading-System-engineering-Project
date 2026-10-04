# MS-0.25 — History-Window Policy

## Status

**LOCKED — Option A: Explicit application configuration**

Baseline: MS-0.24 at `5866ca0`.

## Purpose

MS-0.25 defines who owns the operational history window supplied to the
observation pipeline. It does **not** define a numerical trading lookback.

## Canonical policy

The application supplies the complete operational history window through the
history-window resolver:

```text
Application History Policy
        ↓
ObservationDataWindow
        ↓
ObservationRunner
        ↓
Deterministic Strategy Engines
        ↓
Sufficient history?
    ├── No  → WAIT / INSUFFICIENT_HISTORY
    └── Yes → continue
```

The application-level history resolver has the contract:

```python
Callable[[str, datetime], ObservationDataWindow]
```

It receives the instrument and completed H1 observation boundary and returns
the complete H1/M15 `ObservationDataWindow` to be used for that observation.

## Responsibility boundaries

### Application / configuration

Owns the requested operational history window.

It may eventually provide different windows for different instruments or
runtime configurations. MS-0.25 does not prescribe those values.

### ObservationRunner

Consumes the supplied `ObservationDataWindow`.

It must not:

- invent a lookback duration;
- add a hard-coded candle-count requirement;
- substitute a strategy-specific history window;
- reinterpret adapter retrieval settings as methodology.

### History resolver

Obtains the requested data window.

The resolver is an application/runtime capability. It does not define the
minimum history required by a strategy engine.

### Deterministic strategy engines

Determine whether the supplied history is sufficient for their own already
locked deterministic logic.

Insufficient supplied history remains an observation outcome of
`WAIT / INSUFFICIENT_HISTORY`; MS-0.25 does not alter that behavior.

## Explicit non-canonical values

The following remain **fixtures or lower-level implementation details**, not
ASTER history-policy values:

- H1/M15 durations used in existing tests;
- the H1 boundary resolver's retrieval lookback;
- Twelve Data adapter `lookback_candles` behavior.

None may be promoted into the ASTER strategy-history policy without a separate
methodology decision.

## Non-goals

MS-0.25 does not:

- select a numerical H1 lookback;
- select a numerical M15 lookback;
- define a candle-count threshold;
- change H1 market-structure sufficiency logic;
- change M15 confirmation logic;
- change market-data adapter retrieval behavior;
- make the ObservationRunner responsible for history acquisition policy.

## Compatibility invariant

The observation pipeline continues to receive a concrete
`ObservationDataWindow`. The milestone changes ownership and typing of the
application-level contract, not the semantics of the strategy engines.

## Versioning

The application composition records `history_window_policy = MS-0.25` in its
methodology-version set so persisted observations can identify the policy
baseline used to assemble their operational data window.
