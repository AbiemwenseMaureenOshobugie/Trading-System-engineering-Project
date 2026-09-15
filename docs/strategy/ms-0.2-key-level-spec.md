# MS-0.2 — Key-Level Detection

## 1. Objective

MS-0.2 defines ASTER's deterministic Key-Level Detection layer. It converts approved structural evidence into canonical active Key Levels for downstream setup and confirmation logic.

MS-0.2 answers:

> What valid Key Levels currently exist?

It does **not** select the governing Key Level for an individual setup. That selection belongs to downstream setup/confirmation logic.

## 2. Inputs

MS-0.2 consumes already-established strategy evidence, including:

- validated/meaningful swing zones from MS-0.1A;
- established H1 range-boundary zones from MS-0.1A;
- approved breakout structural events and their associated source level;
- approved role-reversal state transitions on an existing level.

MS-0.2 does not reconstruct H1 market structure or create a second swing-detection algorithm.

## 3. Canonical Key-Level definition

A **Key Level is a canonical structural identity backed by one or more approved source zones, with provenance identifying those sources. The contributing source zones remain authoritative and are preserved. MS-0.2 does not synthesize or arbitrarily select a new canonical geometry when multiple overlapping source zones contribute.**

A Key Level therefore represents an evidence-backed structural identity, not merely a single price and not an independently invented support/resistance line.

## 4. Approved Key-Level sources

### 4.1 Validated Swing

A confirmed meaningful swing from MS-0.1A contributes its immutable canonical swing zone as Key-Level evidence.

- Swing High Zone: `[High, max(Open, Close)]`.
- Swing Low Zone: `[min(Open, Close), Low]`.
- The Key-Level layer does not alter the swing-zone coordinates.

A confirmed-but-not-meaningful swing is not an approved active Key-Level source.

### 4.2 Range Boundary

An established H1 range boundary contributes its immutable boundary zone as Key-Level evidence.

- `range_upper_boundary` is the selected upper resistance zone.
- `range_lower_boundary` is the selected lower support zone.
- Boundary selection and immutability are governed by MS-0.1A.

A boundary is not promoted merely because an earlier swing exists; it must already be an established range boundary.

### 4.3 Breakout Level

A breakout level is evidence attached to an already-established structural level that has been broken as part of an approved breakout event.

The breakout source does not invent a new price-zone width. The associated Key-Level zone is inherited from the structural level involved in the breakout.

A range breakout alone does not establish a trend and does not create a new H1 regime; MS-0.1A records it as a transition event/subtype until sufficient new structure establishes a replacement regime.

### 4.4 Role Reversal

Role Reversal is a state transition of an existing structural level, not an independent method for inventing a new zone.

The existing source zone remains authoritative for the level's price identity. Role-reversal evidence is retained as provenance/state history when the level changes structural role.

## 5. Activation

A Key-Level candidate becomes an **active Key Level only when its underlying approved source has reached its already-defined confirmation/establishment state**.

MS-0.2 introduces no independent activation threshold.

Examples:

- a swing source must already be confirmed/meaningful under MS-0.1A;
- a range-boundary source must already be an established boundary;
- a breakout source must already be associated with the approved breakout event;
- a role-reversal source must already represent an established state transition of an existing level.

## 6. Overlap and identity

If two or more active source zones overlap, they are consolidated into **one Key-Level identity**.

All contributing source evidence, provenance, and source-specific zones are retained.

Overlap is the identity rule. No additional pip, percentage, ATR, volatility, or other proximity tolerance is introduced.

The underlying source zones remain unchanged. MS-0.2 does not calculate a union or intersection zone and does not select one contributing source zone as universally canonical.

## 7. Provenance and source geometry

Each Key Level must preserve enough information to reconstruct why the level exists.

At minimum, provenance must identify:

- the approved source type(s);
- the source evidence reference(s);
- the source-specific zone associated with each contributing source;
- the active/inactive state history.

Multiple source types may coexist on one Key Level.

Source-specific zones remain authoritative. A Key-Level identity does not manufacture a replacement geometry from overlapping zones.

## 8. Activity and retirement

MS-0.2 does not define an independent time-based, distance-based, or generic price-break retirement rule.

A Key Level remains active while its underlying approved source evidence remains structurally valid.

When the underlying source becomes structurally inactive, the Key Level becomes inactive accordingly.

Historical Key-Level evidence remains auditable after deactivation.

A Key Level does not expire merely because time passes or because it has not recently been interacted with.

## 9. Governing Key-Level selection boundary

MS-0.2 detects and maintains active Key Levels but **does not select the governing Key Level for a setup**.

Downstream setup/confirmation logic is responsible for selecting exactly one `setup_key_level` for a qualifying setup according to the setup context.

MS-0.2 must therefore not introduce:

- nearest-level ranking;
- generic level-strength scoring;
- setup-specific proximity ranking;
- risk/reward optimization;
- CP-2 selection logic.

## 10. Deterministic invariants

1. Every active Key Level has at least one approved source evidence.
2. A Key Level is a canonical structural identity, not a single price line.
3. Source provenance is preserved.
4. Source-specific zones are preserved and remain authoritative.
5. Multiple approved sources may contribute to one Key-Level identity.
6. A source must reach its own established confirmation/establishment state before activation.
7. Overlapping active source zones consolidate into one Key-Level identity.
8. Consolidation does not mutate underlying source zones.
9. No undocumented numerical proximity tolerance is introduced.
10. No union or intersection geometry is synthesized from overlapping source zones.
11. Role Reversal changes provenance/state of an existing level; it does not invent a new zone.
12. MS-0.2 does not choose the downstream governing `setup_key_level`.
13. No independent time-based Key-Level expiry is introduced.
14. Key-Level activity follows the structural validity of its underlying source evidence.
15. Historical Key-Level evidence remains auditable after deactivation.
16. Identical approved inputs produce identical Key-Level output and provenance.

## 11. Domain output contract

`KeyLevel` must expose, at minimum:

- a stable Key-Level identifier;
- one or more `KeyLevelSource` provenance values;
- source-specific `PriceZone` values associated with their contributing sources;
- active/inactive state;
- creation/update timestamps;
- source/evidence references;
- state history.

The domain contract must support multiple source types and preserve their authoritative source geometry because K-01 and K-03A require evidence aggregation without arbitrary geometry selection.

## 12. Non-goals

MS-0.2 does not define:

- H1 swing detection;
- H1 regime classification;
- M15 CP-1 confirmation;
- M15 CP-2 confirmation;
- governing setup-key-level selection;
- stop-loss or target calculation;
- CP-2 execution-aware buffer calculation;
- risk authorization;
- governance authorization;
- broker execution;
- AI/ML prediction or interpretation.

## 13. Implementation gate

MS-0.2 methodology decisions K-01 through K-05 and K-03A are closed. Implementation may proceed after the specification-to-domain-contract-to-port-to-test consistency check.
