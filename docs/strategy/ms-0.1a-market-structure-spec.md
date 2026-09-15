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

An opposing swing forms when the next valid opposing candidate appears. Once an opposing swing forms, the candidate identity is immutable. Exactly one opposing swing is active. A newer opposing candidate replaces it only when it is more extreme in the relevant direction; non-replacing candidates remain historical only. A replacement resets opposing-swing tracking.

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

Meaningfulness is a structural-chain property. A confirmed swing becomes meaningful when its structural relationship makes it part of the active structural chain. There is no separate reaction/event state machine and no undocumented pip, ATR, candle-count, or discretionary threshold.

The active chain is a hybrid of chronology and structural relationships:

- chronology preserves development order;
- structural relationships determine current active participation;
- inactive historical swings remain auditable but do not classify current structure;
- a previously excluded meaningful swing may later re-enter the active chain when later structural relationships make it relevant, while retaining its original chronology;
- equal meaningful swings remain in the chain, have no directional relationship, and cannot control structure;
- only the active chain determines current classification, controlling swing, regime, and directional invalidation.

Two-phase establishment applies:

1. **Phase 1:** confirmed swings may serve as references while the first valid meaningful structural sequence is established.
2. **Phase 2:** once structure is established, only the most recent meaningful opposite swing may confirm new structural progression. Confirmed-but-not-meaningful swings cannot do so.

## 6. Structural relationships

Each new meaningful swing is classified by actual relationship, independent of current regime.

- Meaningful high above relevant prior meaningful high → `HH`.
- Meaningful high below relevant prior meaningful high → `LH`.
- Meaningful low above relevant prior meaningful low → `HL`.
- Meaningful low below relevant prior meaningful low → `LL`.
- Overlapping swing zones are equal/neither and do not replace a controlling swing.

Equality is defined only by zone overlap. No numerical tolerance is added.

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

A range breakout is recorded as a structural event/subtype of the transition process, e.g. `RANGE_BREAKOUT_UP` or `RANGE_BREAKOUT_DOWN`. A breakout alone does not establish UPTREND or DOWNTREND. Failed penetration returning into the range does not automatically change RANGE.

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
9. Meaningfulness follows active-chain participation.
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

## 13. Acceptance tests

The implementation must cover the existing MS-0.1A lifecycle tests plus:

- **T-19 — Bounding pair:** actual bounding meaningful high/low zones are selected; chronology alone cannot select them.
- **T-20 — Explicit state evidence:** upper/lower boundary fields are present and correct in `MarketStructureState`.
- **T-21 — Boundary immutability:** later reactions do not change selected zones.
- **T-22 — Alternating reactions:** RANGE requires alternating upper/lower reactions, starting from either side.
- **T-23 — Non-bounding candidate:** an earlier but non-bounding meaningful swing is not promoted to a boundary.
- **T-24 — Cutoff safety:** later boundary candidates/reactions cannot influence an earlier evaluation.

The broader acceptance suite must also demonstrate candidate detection/replacement, opposing-swing tracking, confirmation, meaningfulness, active-chain construction, HH/HL/LH/LL/equality, controlling-swing updates, UPTREND/DOWNTREND establishment and persistence, invalidation/TRANSITION, UNCLEAR fallback, regime conflict handling, deterministic replay, and explanatory structural events.

## 14. Non-goals

MS-0.1A does not define M15 CP-1/CP-2 confirmation, CP-2 execution-aware buffers, risk percentages, session values/timezones, trade/loss counting semantics, broker execution, live authorization, or AI/ML prediction.

## 15. Implementation gate

The RANGE boundary-selection ambiguity is closed. MS-0.1A is specification-complete and may proceed to implementation subject only to normal spec-to-contract-to-port-to-test consistency checks.
