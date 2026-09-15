# MS-0.1A — Test Plan

MS-0.1A tests are organized around deterministic state reconstruction and evidence preservation. The engine must be replayable from the same H1 candles and `evaluation_cutoff`.

## T-19 — Bounding-pair selection

Given multiple meaningful highs and lows, the engine selects the meaningful high zone and meaningful low zone that actually bound the developing range. The first chronological high/low pair is not sufficient by itself.

## T-20 — Explicit boundary evidence

A `MarketStructureState` exposes `range_upper_boundary` and `range_lower_boundary` as explicit `PriceZone` values when selected, and `None` when not selected.

## T-21 — Boundary immutability

After a boundary is selected, later meaningful reactions do not alter its `PriceZone` coordinates.

## T-22 — Alternating boundary reactions

RANGE is not established from a boundary pair alone. Meaningful reactions must alternate between upper and lower boundaries, and the sequence may begin from either boundary.

## T-23 — Non-bounding candidate rejection

A meaningful swing that does not actually bound the developing range is retained as historical structural evidence but is not promoted to an initial boundary merely because it occurred earlier.

## T-24 — Evaluation-cutoff safety

The same historical input evaluated at an earlier cutoff must not incorporate boundary candidates or reactions that occur after that cutoff. Identical candles and cutoff must produce deterministic output.

## Existing MS-0.1A coverage

The implementation must also retain the previously defined tests for candidate detection, dual-candidate rejection, candidate replacement, opposing-swing tracking, confirmation, meaningfulness, active-chain construction, structural relationships, controlling swings, trend establishment, invalidation, transition, UNCLEAR, regime persistence, and deterministic replay.
