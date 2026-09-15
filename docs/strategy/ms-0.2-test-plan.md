# MS-0.2 — Key-Level Detection Test Plan

## Objective

Verify that MS-0.2 deterministically converts approved structural evidence into canonical Key Levels without changing source zones, inventing thresholds, or performing downstream setup selection.

## Acceptance tests

### KLT-01 — Validated Swing source
A confirmed meaningful swing produces a Key-Level candidate using the immutable MS-0.1A swing zone.

### KLT-02 — Range Boundary source
An established `range_upper_boundary` or `range_lower_boundary` produces the corresponding Key-Level evidence without reconstructing or changing the boundary.

### KLT-03 — Breakout Level source
An approved breakout event produces Key-Level evidence tied to the already-established structural level that was broken; no arbitrary new zone is created.

### KLT-04 — Role Reversal source
A role-reversal event preserves the existing canonical zone and records the new provenance/state evidence rather than creating a new zone.

### KLT-05 — Activation gate
Unconfirmed/unestablished source evidence does not create an active Key Level. Source confirmation/establishment is required first.

### KLT-06 — Overlap consolidation
Two active source zones that overlap become one canonical Key Level with all contributing source types and evidence references retained.

### KLT-07 — Non-overlap separation
Distinct non-overlapping active zones remain separate Key Levels.

### KLT-08 — No source-zone mutation
Consolidation does not change the coordinates of any underlying source zone.

### KLT-09 — Multiple provenance
A single Key Level can retain multiple approved source types and evidence references.

### KLT-10 — No governing-level selection
MS-0.2 returns the active Key-Level set and does not select a downstream `setup_key_level`.

### KLT-11 — No independent expiry
A Key Level remains active when its source remains structurally valid, regardless of elapsed time or lack of recent interaction.

### KLT-12 — Source-driven retirement
When the underlying source becomes structurally inactive, the corresponding Key Level becomes inactive while historical evidence remains auditable.

### KLT-13 — No numerical merge tolerance
A merge must not depend on invented pip, percentage, ATR, volatility, or distance thresholds.

### KLT-14 — Deterministic replay
Identical approved inputs produce identical Key-Level identities, zones, provenance, and activity state.

### KLT-15 — MS-0.1A compatibility
MS-0.2 consumes MS-0.1A output without changing market-structure regimes, swing zones, controlling levels, or range-boundary definitions.

### KLT-16 — CP-2 boundary
MS-0.2 exposes valid Key Levels to downstream confirmation logic but does not implement CP-2 rejection/sweep logic or governing-level selection.

## Regression requirement

The complete existing test suite must continue to pass. MS-0.2 tests must be deterministic and must not weaken existing MS-0.1A assertions.
