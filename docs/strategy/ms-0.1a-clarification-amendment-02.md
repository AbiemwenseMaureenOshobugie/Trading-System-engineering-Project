# MS-0.1A Clarification Amendment 02 — Pre-Rework Audit

**Status:** Documentation-only clarification record. No implementation or test files are changed by this amendment.

**Purpose:** Record which reported ambiguities are already determined by the canonical MS-0.1A specification, make only clarifications supported by the existing locked methodology, and keep unresolved methodology decisions as explicit blockers. This document does not authorize implementation assumptions.

## R13 — Opposing-swing tracking reset

**Status: UNRESOLVED — blocks rework of candidate confirmation if that behavior depends on the reset.**

The locked rules establish that the opposing swing tracks the latest more-extreme low/high until confirmation, and that replacing the active opposing swing resets tracking. They do not enumerate the exact tracking state that resets, nor specify which evidence is retained versus cleared.

The implementation must not decide this implicitly. Before reworking `_confirm_candidates`, the specification owner must state:
1. which candidate/opposing-swing references remain active after replacement;
2. which confirmation progress or pending state is cleared;
3. which prior candidates and events remain in immutable historical evidence.

No behavior is selected by this document.

## R21 — Chronological reconsideration order

**Clarification supported by the existing specification:** Reconsider unresolved swings in chronological order of the swing's occurrence (the timestamp of its candidate/swing-point candle), not by the later confirmation timestamp.

**Basis:** The canonical specification defines chronology as the order in which structure developed and requires unresolved swings to be reconsidered in chronological order. The swing-point candle owns the structural extreme. Confirmation time records when confirmation became knowable; it does not redefine when that swing occurred.

The existing specification also says each unresolved swing is reconsidered at most once per pass and outcomes within a pass do not recursively trigger another pass. Those rules remain unchanged.

## R33 — Historical evaluation immutability

**Status: ALREADY SPECIFIED; no new rule required.**

The canonical specification already states that historical evaluations and their emitted evidence are immutable, and that each evaluation and its emitted evidence are immutable. A later evaluation may use additional eligible evidence and may establish a previously unresolved classification or reconsider unresolved participation only through the explicitly defined reconsideration process. It must not mutate the result of an earlier evaluation.

This clarification does not mean the current active chain must be identical across different evaluation cutoffs.

## R61 / R71 — Range-boundary selection and immutability

**Status: SELECTION EVENT AND BOUNDARY IMMUTABILITY ALREADY SPECIFIED; no new rule required.**

The canonical specification defines initial boundary selection as part of first establishing RANGE, through the bounding-pair rule. `range_upper_boundary` and `range_lower_boundary` are `None` until selected and remain immutable once selected. Later reactions validate the selected boundaries but do not change their coordinates.

The existing text does not authorize silently re-deriving or replacing selected boundary coordinates on every evaluation. If a future requirement is intended to permit a new range episode with newly selected boundaries, that must be specified as a distinct state/lifecycle rule before implementation; this amendment does not add one.

## R65 — “Failed penetration returning into the range”

**Status: UNRESOLVED — blocks implementation changes to `_range_breakout`.**

The locked methodology establishes that a failed range-boundary penetration does not automatically invalidate RANGE, that RANGE remains RANGE if it remains structurally valid, and that the observation may be recorded as an event. It does not define the observable candle-close sequence that makes a penetration “failed” or what exact event timing distinguishes a failed penetration from a breakout.

The implementation must not invent a wick rule, close rule, number of candles, or timeout. Before `_range_breakout` is changed, the specification owner must define:
1. what event starts a penetration attempt;
2. what exact observable price/candle condition counts as returning into the range;
3. when the attempt is classified as failed;
4. whether the classification is based on a completed H1 close and how the event is timestamped.

No behavior is selected by this document.

## Rework gate

Option 2 remains the agreed scope: Sections 5–6 plus the reported §7–§9 defects (R56, R57, R59, R68). However, the documentation gate is **not yet fully satisfied**:

- R21, R33, R61/R71 are resolved by the existing contract and the clarifications above.
- R13 remains a blocker for `_confirm_candidates` changes that depend on reset semantics.
- R65 remains a blocker for `_range_breakout` changes.

No engine implementation or conformance tests are authorized by this documentation-only change. The rework must not start until the unresolved R13 and R65 semantics are explicitly approved and incorporated into the canonical specification. After that, write one failing conformance test for each in-scope VIOLATED/MISSING requirement before changing implementation.