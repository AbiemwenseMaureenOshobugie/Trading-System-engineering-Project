# MS-0.1A — H1 Market Structure Engine

## 1. Purpose

MS-0.1A defines ASTER's deterministic H1 Market Structure Engine. It consumes validated, normalized, completed H1 candles plus an explicit `evaluation_cutoff` and returns one canonical `MarketStructureState`.

It owns candidate reconstruction, confirmation, meaningful structural participation, active-chain relationships, controlling swing selection, H1 regime classification, and structural evidence. It does not own M15 confirmation, risk, governance, broker execution, or AI/ML interpretation.

## 2. Evaluation boundary

Only completed H1 candles whose close/open interval is at or before `evaluation_cutoff` may influence the result. Future candles must never affect historical evaluation. Insufficient history yields initial `UNCLEAR`; no specific candle-count threshold is invented here.

## 3. Candidate lifecycle

Candidate identification uses exactly three consecutive candles `(left, middle, right)`.

- Candidate High: `middle.high > left.high` and `middle.high > right.high`.
- Candidate Low: `middle.low < left.low` and `middle.low < right.low`.
- The middle candle owns the structural extreme.
- Nested candidates are retained without parent/child hierarchy.
- If a newer candidate competes with an unconfirmed candidate, the newer candidate wins.
- If a middle candle satisfies both high and low conditions, the window is dual/ambiguous and produces neither candidate.
- Subsequent windows continue normally after a dual candidate.

An opposing swing forms when the next valid opposing candidate appears. Once an opposing swing forms, the candidate identity is immutable. Exactly one opposing swing is active. A newer opposing candidate replaces the active opposing swing only when it is more extreme in the relevant direction; non-replacing candidates remain historical only. When replacement occurs, rebind the pending confirmation predicate to the new opposing reference. The active candidate's identity, zone, and origin remain unchanged. Record the replacement and both the old and new opposing references in `structural_events`; retain prior candidate and event evidence as history. Replacement does not create a new active candidate or alter the active candidate's zone or origin.

## 4. Confirmation and zones

A candidate becomes a confirmed swing only after a completed H1 candle closes beyond the extreme of its active opposing swing:

- Candidate High → close below opposing low extreme.
- Candidate Low → close above opposing high extreme.

Confirmation does not imply meaningfulness and confirmed swings do not expire merely with time.

Canonical zones are immutable:

- Swing High Zone: `[High, max(Open, Close)]`.
- Swing Low Zone: `[min(Open, Close), Low]`.

Reactions may provide evidence but never modify these zone boundaries.

## 5. Meaningfulness and active chain

Meaningfulness is a structural-chain property. Confirmation establishes that a swing is structurally confirmed; it does not establish that the swing is meaningful.

A confirmed swing becomes meaningful only when it is accepted into the active structural chain under the deterministic procedure defined in this section. There is no separate reaction/event state machine and no undocumented pip, ATR, candle-count, or discretionary threshold.

The active chain is a hybrid of chronology and structural relationships:

- chronology preserves development order;
- structural relationships determine current active participation;
- inactive historical swings remain auditable but do not classify current structure;
- a confirmed swing excluded from the active structural chain remains excluded from that chain; it is not silently reconsidered or reinstated by later price action;
- if later price action produces a new confirmed swing, that new swing is evaluated under the normal meaningfulness procedure;
- an unresolved swing is distinct from an excluded swing: unresolved swings may be re-evaluated in later evaluations as additional confirmed structural evidence becomes available, but excluded swings are not re-evaluated or reinstated under this version of MS-0.1A;
- equal meaningful swings remain in the chain, have no directional relationship, and cannot control structure;
- only the active chain determines current classification, controlling swing, regime, and directional invalidation.

Two-phase establishment applies:

1. **Phase 1 — structural establishment:** confirmed swings may be retained as reference observations while the engine evaluates whether the first valid meaningful structural sequence can be established. A confirmed swing is not automatically meaningful merely because it is available as a reference.
2. **Phase 2 — established structure:** Phase 2 begins only after the directional establishment requirements in Section 7 are satisfied. Once established, only the most recent meaningful opposite swing may confirm new structural progression. Confirmed-but-not-meaningful swings cannot do so.

During Phase 1, the engine must use the same-kind reference and structural-consistency rules below. It must not introduce an additional bootstrap or bridge rule that is not defined by this specification.

### Active structural sequence

The active structural sequence is the chronologically ordered set of confirmed swings accepted as meaningful under Sections 5 and 6 for the current evaluation. Confirmed observations that are excluded or unresolved are not members of this sequence. Historical evaluations and their emitted evidence remain immutable; a later evaluation may produce a different active sequence only by applying the explicit re-evaluation rule for unresolved swings below.

## 6. Structural relationships

Each confirmed swing is evaluated for same-kind classification before its meaningfulness is determined. Classification is based on the actual price-zone relationship, independent of current regime.

### Same-kind reference selection

For a candidate confirmed HIGH, the reference is the most recent previously accepted meaningful HIGH in the active structural sequence. For a candidate confirmed LOW, the reference is the most recent previously accepted meaningful LOW in the active structural sequence.

- Confirmed HIGH above its same-kind reference → `HH`.
- Confirmed HIGH below its same-kind reference → `LH`.
- Confirmed LOW above its same-kind reference → `HL`.
- Confirmed LOW below its same-kind reference → `LL`.
- Overlapping swing zones are equal/neither and do not replace a controlling swing.
- A confirmed swing excluded from the active sequence does not replace its same-kind reference.
- A HIGH is never compared directly with a LOW to determine `HH` or `LH`; a LOW is never compared directly with a HIGH to determine `HL` or `LL`.
- If an accepted meaningful same-kind reference exists at the swing's confirmation evaluation, the engine records both the relationship classification and the exact reference swing used. That classification and reference are immutable.
- If no accepted meaningful same-kind reference exists, the engine records `CLASSIFICATION_UNRESOLVED`; it must not invent a bootstrap reference. At a later evaluation, the engine may establish the initial relationship classification when a valid same-kind reference becomes available. At that point, it records the reference used and freezes both the classification and reference. This establishes a previously unknown classification; it does not recalculate an established classification.

Equality is defined only by zone overlap. No numerical tolerance is added.

### Conflicting structural evidence and re-evaluation

Same-kind classification and active-chain participation are separate determinations. A same-kind relationship alone does not prove that a swing extends the active structural sequence.

When same-kind classification and available opposite-kind structural evidence conflict, or evidence is insufficient to determine active-chain participation, the swing remains a confirmed observation but is unresolved for that evaluation. It must not extend the active chain, become controlling, or establish a directional regime while unresolved.

The engine must expose the condition in `structural_events` using `SWING_CONFIRMED_UNRESOLVED` with evidence sufficient to identify the confirmed swing and the unresolved reason. The unresolved swing is not included in `meaningful_highs` or `meaningful_lows` while unresolved. It remains visible as a confirmed observation in structural evidence.

An unresolved swing is reconsidered when a newly confirmed swing receives an admission or exclusion outcome for the active structural sequence. Each such outcome event starts one reconsideration pass over unresolved swings in chronological order; each unresolved swing is reconsidered at most once during that pass. Outcomes within a pass do not recursively trigger another pass. Only a later newly confirmed swing's admission or exclusion outcome may trigger the next pass.

During reconsideration, an unresolved swing's same-kind classification may be established only if it was previously `CLASSIFICATION_UNRESOLVED` and a valid same-kind reference has become available. Once established, the classification and reference are frozen. An already established classification and its recorded reference are never recalculated. Admission is reconsidered separately using the updated confirmed structural evidence and Sections 5–7. A previously unresolved swing may be admitted only if the updated evidence makes its classification and active-chain participation consistent; otherwise it remains unresolved. Each evaluation and its emitted evidence are immutable.

A swing is admitted to the active structural chain only when its same-kind classification and the available opposite-kind structural evidence are consistent with the active structural sequence. If the evidence conflicts or is insufficient to determine participation, the swing remains confirmed but unresolved for that evaluation. A swing explicitly excluded as non-extending remains excluded and is not re-evaluated or reinstated under this version.

## 7. Controlling swing and trend regimes

The controlling swing is the most recent meaningful opposite swing that established/progressed the current directional structure.

### UPTREND

Requires at least two meaningful `HH`s, at least two meaningful `HL`s, an intact controlling `HL`, and no completed H1 close below that controlling `HL`. A single HH/HL pair is insufficient. Contrary meaningful evidence does not replace the regime while the controlling HL remains intact.

### DOWNTREND

Requires at least two meaningful `LH`s, at least two meaningful `LL`s, an intact controlling `LH`, and no completed H1 close above that controlling `LH`. A single LH/LL pair is insufficient. Contrary meaningful evidence does not replace the regime while the controlling LH remains intact.

## 8. Invalidation and TRANSITION

Invalidation is close-based, not wick-based:

- UPTREND → completed H1 close below controlling HL.
- DOWNTREND → completed H1 close above controlling LH.

Wicks warn; H1 closes confirm. Invalidation does not automatically establish the opposite trend.

`TRANSITION` exists only after an established regime is invalidated/structurally changed and a replacement regime is not yet established. Invalidated structure remains historical but becomes inactive and non-controlling. Old invalidated structure is not silently revived. Each later invalidation of a replacement regime creates a distinct transition episode.

## 9. RANGE

RANGE is not the complement of the two trend regimes. A valid range requires:

1. an upper resistance boundary zone;
2. a lower support boundary zone;
3. meaningful reactions to those boundaries;
4. alternating upper/lower boundary reactions, beginning from either side;
5. no sustained directional progression sufficient for UPTREND or DOWNTREND.

### Initial boundary selection — locked bounding-pair rule

When RANGE is first being established, select the **bounding pair**:

- `range_upper_boundary` is the meaningful swing-high zone that actually bounds the developing range;
- `range_lower_boundary` is the meaningful swing-low zone that actually bounds the developing range.

Chronological order does not select the pair. A swing is not promoted merely because it appeared first; it must actually bound the developing range.

Selected boundary zones are immutable. Later reactions validate them but never change their coordinates.

### Boundary reaction

A meaningful high is an upper-boundary reaction when its canonical swing-high zone overlaps the upper boundary. A meaningful low is a lower-boundary reaction when its canonical swing-low zone overlaps the lower boundary. No numerical proximity tolerance is introduced.

### Range establishment

The alternating reaction sequence may begin from either boundary. Non-directional evidence that does not satisfy the complete RANGE conditions remains `UNCLEAR`.

### Range breakout

A range breakout is recorded as a structural event/subtype of the transition process, e.g. `RANGE_BREAKOUT_UP` or `RANGE_BREAKOUT_DOWN`. A breakout alone does not establish UPTREND or DOWNTREND. A boundary penetration is evaluated from a completed H1 candle that closes at or beyond the selected boundary in the breakout direction. “At or beyond” means the candle close is on or past the outer edge of the boundary zone, inclusive. The immediately following H1 candle determines whether that penetration failed or was confirmed: if that candle closes inside the selected range, the penetration is failed and the range is not invalidated; if it closes at or beyond the same selected boundary in the breakout direction, the penetration is confirmed. If no following completed H1 candle is available, the penetration remains provisional and no breakout is confirmed yet. If the following candle closes beyond the opposite range boundary, the original penetration is failed; the opposite-direction penetration is evaluated as a separate event under this same immediate-following-candle rule. This immediate-return rule governs range invalidation only. It does not alter candidate identification, opposing-swing confirmation, meaningfulness, classification, or active-chain participation under Sections 3–6. “Immediately following” means the next completed candle in the evaluated sequence; gaps in market time do not affect the rule.

## 10. UNCLEAR and persistence

`UNCLEAR` is the fallback when evidence is insufficient, ambiguous, internally conflicting, or does not establish UPTREND, DOWNTREND, RANGE, or a post-invalidation transition.

UNCLEAR may move directly to the first valid established regime. TRANSITION is reserved for change after an established regime.

An established regime persists while its defining conditions remain valid. Isolated opposing evidence does not replace it. Initial evidence that cannot validly distinguish a regime remains UNCLEAR.

## 11. Domain output contract

`MarketStructureState` must expose at minimum:

- `regime`;
- `structure_version`;
- `meaningful_highs`;
- `meaningful_lows`;
- `controlling_level` where applicable;
- `range_upper_boundary` where selected;
- `range_lower_boundary` where selected;
- `structural_events`;
- `evaluated_at`.

Boundary fields are explicit `Optional[PriceZone]` evidence. They are `None` until selected and remain immutable once selected.

## 12. Deterministic invariants

1. Candidate windows contain exactly three candles.
2. Dual candidates produce neither candidate.
3. Newer competing unconfirmed candidates replace older ones.
4. Candidate identity becomes immutable when an opposing swing forms.
5. Exactly one opposing swing is active.
6. Only a more extreme opposing candidate replaces it.
7. Confirmation requires a completed H1 close beyond the opposing extreme.
8. Confirmation does not imply meaningfulness.
9. Meaningfulness requires acceptance into the active structural sequence under Sections 5 and 6.
10. Swing zones are immutable.
11. Equality is zone overlap.
12. Equal swings never become controlling.
13. Current classification uses the active chain only.
14. Trend invalidation requires a completed H1 close beyond the controlling level.
15. Invalidation does not automatically reverse the regime.
16. RANGE is not `not UPTREND and not DOWNTREND`.
17. RANGE requires alternating boundary reactions.
18. Initial RANGE boundaries use the bounding-pair rule.
19. Boundary evidence is explicit in `MarketStructureState`.
20. Boundary zones remain immutable after selection.
21. Future candles after `evaluation_cutoff` cannot influence the result.
22. Historical evidence remains auditable when inactive.
23. No undocumented numerical thresholds may be introduced.
24. Identical candles and cutoff produce identical state and structural events.
25. Same-kind classification compares a confirmed swing only with the most recent previously accepted meaningful swing of the same kind in the active sequence.
26. A confirmed swing excluded as non-extending does not replace its same-kind reference and is not silently reinstated.
27. Conflicting or insufficient same-kind/opposite-kind evidence produces an observable unresolved confirmed swing; it is not admitted to the active sequence until a later evaluation resolves it under Section 6.
28. Phase 2 begins only after the applicable directional establishment requirements in Section 7 are satisfied.
29. If a same-kind reference exists at confirmation, the relationship classification and exact reference swing are recorded and immutable; an initially unresolved classification may be established later when a valid same-kind reference becomes available, after which both are immutable.
30. A newly confirmed swing's admission or exclusion triggers one reconsideration pass over unresolved swings in chronological order; each unresolved swing is reconsidered at most once per pass, and outcomes within a pass do not recursively trigger another pass.
31. Re-evaluation never rewrites prior evaluation output; a swing explicitly excluded as non-extending is not re-evaluated or reinstated under this version.

## 13. Acceptance tests

The implementation must cover the existing MS-0.1A lifecycle tests plus:

- **T-19 — Bounding pair:** actual bounding meaningful high/low zones are selected; chronology alone cannot select them.
- **T-20 — Explicit state evidence:** upper/lower boundary fields are present and correct in `MarketStructureState`.
- **T-21 — Boundary immutability:** later reactions do not change selected zones.
- **T-22 — Alternating reactions:** RANGE requires alternating upper/lower reactions, starting from either side.
- **T-23 — Non-bounding candidate:** an earlier but non-bounding meaningful swing is not promoted to a boundary.
- **T-24 — Cutoff safety:** later boundary candidates/reactions cannot influence an earlier evaluation.

The broader acceptance suite must also demonstrate candidate detection/replacement, opposing-swing tracking, confirmation, meaningfulness, active-chain construction, HH/HL/LH/LL/equality, controlling-swing updates, UPTREND/DOWNTREND establishment and persistence, invalidation/TRANSITION, UNCLEAR fallback, regime conflict handling, deterministic replay, and explanatory structural events.

The amended contract additionally requires tests for: confirmation without meaningfulness; same-kind-only comparison; exclusion preserving the prior same-kind reference; unresolved-state visibility outside `meaningful_highs`/`meaningful_lows`; frozen classification and recorded reference when classification is established; later establishment of an initially unresolved classification when a same-kind reference becomes available; one reconsideration per unresolved swing per structural-sequence-change pass, processed chronologically without recursive re-triggering; re-evaluation without changing prior evaluation output; and Phase 2 entry only after Section 7 directional establishment requirements are satisfied.

## 14. Non-goals

MS-0.1A does not define M15 CP-1/CP-2 confirmation, CP-2 execution-aware buffers, risk percentages, session values/timezones, trade/loss counting semantics, broker execution, live authorization, or AI/ML prediction.

## 15. Implementation gate

The RANGE boundary-selection ambiguity is closed. This amendment clarifies meaningfulness, same-kind reference selection, one-way exclusion, and observable deferral of conflicting evidence. The unresolved-swing re-evaluation rule is explicit and bounded, while prior evaluations remain immutable. With invariants 1–28 preserved and invariants 29–31 appended, this specification is frozen as the canonical contract for the MS-0.1A implementation rework. The current implementation must be audited and reworked against this specification before merge.
