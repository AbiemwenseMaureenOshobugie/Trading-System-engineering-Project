# MS-0.1A Clarification Amendment 04 — Controlling Swing, Episode Membership, and Persistence

**Status:** Documentation-only clarification. No implementation or test files are changed in this amendment.
**Canonical target:** `docs/strategy/ms-0.1a-market-structure-spec.md`
**Basis:** User-confirmed Q1 = (c), most recent non-invalidated controlling swing; Q2 = (a), post-invalidation swings only.

## Section A — Controlling-swing selection (§7)

The controlling swing is the most recent meaningful opposite swing in the current structural episode that has not been invalidated by a completed H1 close beyond its boundary. A newly admitted meaningful swing of the same kind replaces the previous controlling swing. An invalidated swing can no longer control the established structure. No additional survival test is required before a newer swing can become controlling.

## Section B — First establishment vs. TRANSITION (§7 and §10)

When the directional establishment requirements are first satisfied within the evaluated candles and no prior established regime has been invalidated within those candles, the regime is UPTREND (or DOWNTREND). TRANSITION is returned only when a previously established regime has been invalidated within the evaluated candles and no replacement regime has yet been established.

## Section C — Transition-episode membership (§8)

A transition episode begins at the first completed candle that closes beyond the controlling level of an established regime. The episode includes only swings confirmed after that invalidating close. The invalidating candle belongs to the prior episode. Swings from the prior episode do not count toward the directional establishment requirements of any subsequent regime.

## Section D — Persistence (§10)

Persistence is a property of the inputs. The regime is re-derived on each evaluation from the candles in scope and the evaluation cutoff. It persists across evaluations exactly when the defining conditions of Section 7 remain valid.

## Section E — Deterministic invariants

Append the following invariants to the canonical specification:

32. The controlling swing is the most recent non-invalidated meaningful opposite swing in the current episode; a newly admitted meaningful swing of the same kind replaces the previous controlling swing.
33. A transition episode contains only swings confirmed after the invalidating close; prior-episode swings do not count toward later establishment.
34. First establishment is reported as UPTREND or DOWNTREND, not as TRANSITION.
35. TRANSITION requires an invalidation within the evaluated candles; it is not returned when no established regime has been invalidated in that window.
36. Regime persistence is a property of the inputs; the regime is re-derived on each evaluation.

## Section F — Acceptance tests

Append the following acceptance requirements:

- Controlling-swing selection moves to a more recent non-invalidated swing when one is admitted.
- Controlling-swing clears when invalidated; the engine does not carry an invalidated swing as controlling.
- After invalidation, prior-episode swings do not count toward directional establishment of a replacement regime.
- First establishment of 2-HH/2-HL returns UPTREND, not TRANSITION (and the symmetric DOWNTREND case).
- TRANSITION is returned only after an invalidation within the evaluated candles.
- Regime persists across evaluations when its defining conditions are unchanged.

## Scope and change control

This amendment changes documentation only. It does not authorize implementation or test changes in the same change set. The amendment file is the decision record; the edits to the canonical specification are the binding contract. Implementation and tests must be changed only after this contract is reviewed and merged.
