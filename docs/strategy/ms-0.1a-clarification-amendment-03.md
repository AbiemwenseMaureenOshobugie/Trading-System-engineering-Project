# MS-0.1A Clarification Amendment 03 — Opposing-Swing Rebinding and Failed Penetration

**Status:** Documentation-only clarification. No implementation or test files are changed.

**Canonical target:** `docs/strategy/ms-0.1a-market-structure-spec.md`

## R13 — Opposing-swing rebinding (§3)

When a more-extreme opposing candidate replaces the active opposing swing, rebind the pending confirmation predicate to the new opposing reference. The active candidate's identity, zone, and origin remain unchanged. Record the replacement and the old and new opposing references in `structural_events`. Preserve prior candidates and events as historical evidence.

This is a reference rebinding, not a new active-candidate creation.

## R65 — Failed range-boundary penetration (§9)

A boundary penetration is evaluated from a completed H1 candle that closes at or beyond the selected boundary in the breakout direction. “At or beyond” means the close is on or past the outer edge of the boundary zone, inclusive. The immediately following H1 candle determines the outcome:

- If it closes inside the selected range, the penetration is failed and the range is not invalidated.
- If it closes at or beyond the same selected boundary in the breakout direction, the penetration is confirmed.
- If no following completed H1 candle is available, the penetration remains provisional; no breakout is confirmed yet.
- If the following candle closes beyond the opposite range boundary, the original penetration is failed and the opposite-direction penetration is evaluated as a separate event under the same immediate-following-candle rule.

This immediate-return rule applies to range invalidation only. It does not affect candidate identification, confirmation, meaningfulness, classification, or active-chain rules in Sections 3–6.

## Scope and change control

This amendment resolves R13 and R65 for the agreed MS-0.1A Option 2 rework. It changes documentation only. It does not authorize implementation or test changes in this commit. The rework must still follow the agreed test-first process against the frozen canonical specification.
