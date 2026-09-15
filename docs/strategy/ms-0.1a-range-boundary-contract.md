# MS-0.1A — RANGE Boundary Contract

## Status

Locked and implementation-ready.

## Initial boundary selection

When RANGE is first being established, the engine selects the **bounding pair**:

- `range_upper_boundary`: the meaningful swing-high zone that actually bounds the developing structural range.
- `range_lower_boundary`: the meaningful swing-low zone that actually bounds the developing structural range.

Chronological order does not determine which swing is selected as a boundary. A swing is not promoted merely because it appeared first; it must actually bound the developing range.

The selected zones are canonical and immutable. Subsequent reactions validate the boundaries but do not modify their zone coordinates.

## Boundary evidence

`MarketStructureState` exposes the selected boundaries explicitly:

- `range_upper_boundary: Optional[PriceZone]`
- `range_lower_boundary: Optional[PriceZone]`

Both are `None` unless the corresponding boundary has been selected.

The state therefore carries the boundary evidence required to explain a RANGE classification without reconstructing it from future data.

## RANGE establishment

After candidate boundaries are selected, meaningful swing reactions must alternate between the upper and lower boundaries. The sequence may begin at either boundary.

A high is an upper-boundary reaction when its canonical swing-high zone overlaps the upper boundary zone. A low is a lower-boundary reaction when its canonical swing-low zone overlaps the lower boundary zone.

RANGE is established only when the alternating boundary-reaction requirements are satisfied and no sustained directional progression sufficient for UPTREND or DOWNTREND exists.

Non-directional structure that does not satisfy these conditions remains `UNCLEAR`.

## Deterministic constraints

- Boundary selection uses only meaningful structural evidence available at `evaluation_cutoff`.
- Future candles cannot influence boundary selection or reaction validation.
- No pip, percentage, ATR, candle-count, or discretionary proximity threshold is introduced.
- Boundary zones are never widened, narrowed, or moved because of later reactions.
- A non-bounding meaningful swing remains historical evidence and is not silently promoted to a boundary.

## Acceptance tests T-19 through T-24

- **T-19 — Bounding pair:** initial upper/lower boundaries are selected from the meaningful swing zones that actually bound the developing range; chronology alone cannot select them.
- **T-20 — Explicit state evidence:** `MarketStructureState` exposes the selected upper and lower boundary zones explicitly.
- **T-21 — Boundary immutability:** later reactions do not modify either selected boundary zone.
- **T-22 — Alternating reactions:** RANGE requires alternating upper/lower boundary reactions, beginning from either side.
- **T-23 — Non-bounding candidate:** a meaningful swing that does not bound the developing range is not promoted to a boundary merely because it occurs earlier.
- **T-24 — Cutoff safety:** changing `evaluation_cutoff` excludes later boundary evidence and cannot alter an earlier evaluation through look-ahead.
