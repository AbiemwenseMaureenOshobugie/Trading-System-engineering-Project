# MS-0.2 — Key-Level Source Contract

This document defines the deterministic source-to-Key-Level mapping used by MS-0.2. It does not introduce new trading methodology beyond the locked MS-0.2 decisions and previously established H1 structure rules.

## 1. Source contract

| Source | Activation prerequisite | Source geometry | Provenance role |
|---|---|---|---|
| `VALIDATED_SWING` | Confirmed meaningful swing under MS-0.1A | Immutable swing high/low zone | Direct structural evidence |
| `RANGE_BOUNDARY` | Established H1 range boundary under MS-0.1A | Immutable selected upper/lower boundary zone | Range-structure evidence |
| `BREAKOUT_LEVEL` | Approved breakout event tied to an existing structural level | Inherit the associated structural level's zone | Breakout-state evidence |
| `ROLE_REVERSAL` | Established role transition of an existing level | Inherit the existing Key-Level source zone | State/provenance evidence |

## 2. Validated Swing mapping

For a meaningful swing:

- Swing High Zone = `[High, max(Open, Close)]`.
- Swing Low Zone = `[min(Open, Close), Low]`.

These coordinates are inherited from MS-0.1A and are immutable at the Key-Level layer.

## 3. Range Boundary mapping

For an established H1 range:

- `range_upper_boundary` is the canonical upper resistance zone.
- `range_lower_boundary` is the canonical lower support zone.

The Key-Level layer consumes these explicit state fields rather than reconstructing the range.

## 4. Breakout Level mapping

A breakout level must reference an already-established structural level. MS-0.2 does not create a new arbitrary zone around the breakout price.

For a range breakout, the associated boundary remains the structural source level. The breakout is retained as provenance/event evidence while the H1 regime remains governed by MS-0.1A.

## 5. Role Reversal mapping

Role Reversal is not an independent zone-construction algorithm.

It records that an existing structural level has changed role. The existing source zone remains authoritative. Role-reversal evidence is retained as provenance/state history.

## 6. Consolidation contract

When active source zones overlap:

1. create/retain one Key-Level identity;
2. retain every contributing source type;
3. retain every contributing evidence reference;
4. retain every contributing source-specific `PriceZone`;
5. do not alter any source-zone coordinates;
6. do not introduce a numerical merge tolerance;
7. do not synthesize a union or intersection zone;
8. do not arbitrarily select one source zone as universally canonical.

The Key-Level identity aggregates provenance; source-specific zones remain authoritative.

## 7. Activity contract

A source contributes an active Key Level only after its own source-level confirmation/establishment state is satisfied.

A Key Level becomes inactive when the underlying source evidence becomes structurally inactive. There is no independent age or generic price-break expiry rule.

## 8. Domain representation

The `KeyLevel` domain object stores:

- `source_types`: all approved source types contributing to the identity;
- `source_zones`: the authoritative source-specific `(KeyLevelSource, PriceZone)` pairs;
- active/inactive state;
- provenance/evidence references;
- state history.

`zone_definition` is intentionally not a mandatory field. MS-0.2 does not manufacture a single geometry when multiple source zones contribute to one Key-Level identity.

## 9. Downstream boundary

The source contract ends with a set of active/inactive Key Levels. Selection of exactly one governing `setup_key_level` is a downstream responsibility and is outside MS-0.2.
