# MS-0.1A — H1 Market Structure Engine

## 1. Purpose

MS-0.1A defines the deterministic H1 Market Structure Engine for ASTER.

The engine consumes validated, normalized, completed H1 candles and produces one canonical `MarketStructureState` at an explicit evaluation cutoff.

The engine is responsible for reconstructing structural swings, determining meaningful structural participation, classifying structural relationships, maintaining the active structural chain, identifying the controlling swing, and classifying the H1 regime.

It does not perform M15 confirmation, risk calculation, governance authorization, broker execution, or AI/ML interpretation.

## 2. Objective

For a supplied H1 history and evaluation cutoff, the engine must deterministically answer:

1. Which three-candle patterns are candidate highs/lows?
2. Which candidate is currently active when candidates compete?
3. Which opposing swing is being tracked for an active candidate?
4. Which candidates are confirmed swings?
5. Which confirmed swings are meaningful under the active structural chain rules?
6. What is the structural relationship of each meaningful swing: HH, HL, LH, LL, or equal/neither?
7. Which meaningful swing controls the established directional structure?
8. What H1 regime is currently established: `UPTREND`, `DOWNTREND`, `RANGE`, `TRANSITION`, or `UNCLEAR`?
9. Which structural events explain the resulting state?

## 3. Inputs

### 3.1 Required inputs

- Validated and normalized H1 `MarketCandle` sequence.
- Explicit `evaluation_cutoff`.

### 3.2 Candle eligibility

Only completed H1 candles whose close/open interval is at or before the evaluation cutoff may influence the result.

Future candles must not influence historical evaluation.

The engine must not infer a structural boundary or state from candles after the cutoff.

### 3.3 Bootstrap

The engine may bootstrap from sufficient historical H1 data rather than waiting for newly generated candles.

A configured minimum historical lookback may be required by the application, but the MS-0.1A specification does not invent a specific candle count.

If the available history is insufficient to establish valid structure, the initial regime is `UNCLEAR`.

## 4. Candidate Swing Identification

Candidate identification is the handbook-defined structural pattern.

### 4.1 Candidate High

For three consecutive candles `(left, middle, right)`:

`middle.high > left.high` and `middle.high > right.high`.

The middle candle owns the candidate structural high.

### 4.2 Candidate Low

For three consecutive candles `(left, middle, right)`:

`middle.low < left.low` and `middle.low < right.low`.

The middle candle owns the candidate structural low.

### 4.3 Fixed three-candle window

Candidate identification always uses exactly the immediately preceding, middle, and immediately following candles.

### 4.4 Nested candidates

Nested candidates are retained and evaluated exactly like ordinary candidates. No parent/child hierarchy is created.

### 4.5 Competing consecutive candidates

When a newer candidate replaces an unconfirmed candidate, the newer candidate becomes the active candidate.

The replaced candidate and its unconfirmed opposing-swing tracking become inactive for the current structural process.

### 4.6 Dual candidate

If the middle candle simultaneously satisfies Candidate High and Candidate Low, the window is classified as dual/ambiguous and generates neither candidate.

Subsequent windows continue to be evaluated normally.

## 5. Opposing-Swing Tracking

### 5.1 Formation

An opposing swing forms when the opposing candidate is identified after the active candidate.

- Candidate High → subsequent valid Candidate Low.
- Candidate Low → subsequent valid Candidate High.

### 5.2 Candidate immutability

Once an opposing swing forms, the candidate becomes immutable.

The candidate's identity, timestamp, and structural extreme cannot change.

### 5.3 Dynamic opposing swing

The active opposing swing may update while confirmation remains pending.

For a Candidate High, a newer opposing Candidate Low replaces the current opposing swing only when the newer low is more extreme (lower).

For a Candidate Low, a newer opposing Candidate High replaces the current opposing swing only when the newer high is more extreme (higher).

Non-replacing opposing candidates are retained historically but have no active structural role.

There is exactly one active candidate and one active opposing swing in the current structural process.

## 6. Confirmation

A candidate becomes a confirmed swing when a completed H1 candle closes beyond the extreme of its active opposing swing.

- Candidate High: completed H1 close beyond the opposing swing's low extreme.
- Candidate Low: completed H1 close beyond the opposing swing's high extreme.

Confirmation changes candidate status only. It does not automatically make the swing meaningful.

A confirmed swing does not expire merely because time passes.

## 7. Swing Zones

The canonical swing zones are fixed at creation.

### 7.1 Swing High Zone

`[High, max(Open, Close)]`

### 7.2 Swing Low Zone

`[min(Open, Close), Low]`

Subsequent market reactions may provide evidence about structural validity or quality, but they do not modify the zone boundaries.

## 8. Meaningfulness

Meaningfulness is a property of a confirmed swing's structural participation, not a separate event sequence.

A confirmed swing becomes meaningful when its structural relationship makes it part of the active structural chain under the established structural-chain rules.

The engine must therefore keep these states distinct:

`Candidate → Opposing Swing → Confirmed Swing → Meaningful Swing`

Confirmation alone is insufficient for meaningfulness.

No additional pip, ATR, candle-count, or discretionary threshold is introduced for meaningfulness.

## 9. Active Structural Chain

The active chain is a hybrid of chronology and structural relationships.

- Chronology preserves the actual development sequence.
- Structural relationships determine current active participation.
- Historical meaningful swings remain preserved.
- Structurally inactive historical swings do not participate in current HH/HL/LH/LL classification.
- A previously excluded meaningful swing may later become active again if subsequent structural relationships make it relevant, while retaining its original chronological position.
- Equal meaningful swings remain in the active chain but have no directional relationship.
- Equal meaningful swings cannot become controlling swings.

Only the active structural chain determines current structural classification, controlling swing, regime, and directional invalidation.

## 10. Structural Relationship Classification

A new meaningful swing is always classified by its actual structural relationship, independent of the current regime.

### 10.1 Highs

Compare a meaningful swing high with the relevant prior meaningful high:

- Higher → `HH`
- Lower → `LH`
- Equal/overlapping zones → neither `HH` nor `LH`

### 10.2 Lows

Compare a meaningful swing low with the relevant prior meaningful low:

- Higher → `HL`
- Lower → `LL`
- Equal/overlapping zones → neither `HL` nor `LL`

### 10.3 Equality

Two swing zones are equal when they overlap.

No pip, percentage, or ATR tolerance is added.

An equal swing does not replace a controlling swing and cannot become controlling.

## 11. Two-Phase Structural Establishment

### Phase 1 — Structural Establishment

Confirmed swings may serve as references for completing the first meaningful structural sequence.

The first valid structural sequence establishes the initial structural direction from the actual relationships present.

### Phase 2 — Established Structure

Once structure is established, only the most recent meaningful opposite swing may confirm a new candidate's structural progression.

Confirmed-but-not-meaningful swings cannot confirm new structural candidates in Phase 2.

No arbitrary swing count is introduced solely to declare structure established.

## 12. Controlling Swing

The controlling swing is the most recent meaningful opposite swing that established the current directional structure.

### UPTREND

The controlling swing is the most recent meaningful `HL` that established/progressed the up structure.

### DOWNTREND

The controlling swing is the most recent meaningful `LH` that established/progressed the down structure.

A newer meaningful opposite swing immediately becomes controlling when it establishes structural progression.

An equal meaningful swing never replaces the controlling swing.

## 13. UPTREND

`UPTREND` requires:

- at least two meaningful `HH`s;
- at least two meaningful `HL`s;
- an intact controlling `HL`;
- no completed H1 close beyond the controlling `HL` against the established up structure.

A single HH/HL pair is insufficient to establish UPTREND.

A contrary meaningful structure, such as an `LH`, does not by itself change the regime while the controlling HL remains intact.

## 14. DOWNTREND

`DOWNTREND` requires:

- at least two meaningful `LH`s;
- at least two meaningful `LL`s;
- an intact controlling `LH`;
- no completed H1 close beyond the controlling `LH` against the established down structure.

A single LH/LL pair is insufficient to establish DOWNTREND.

A contrary meaningful structure, such as an `HL`, does not by itself change the regime while the controlling LH remains intact.

## 15. H1 Invalidation

H1 structural invalidation is based on a completed H1 close, not a wick.

- UPTREND invalidates when a completed H1 candle closes below the controlling HL.
- DOWNTREND invalidates when a completed H1 candle closes above the controlling LH.

Wicks warn; H1 closes confirm.

Invalidation ends the established directional regime. It does not automatically establish the opposite trend.

## 16. TRANSITION

`TRANSITION` exists only after an established regime has undergone structural invalidation/change and the replacement regime has not yet been established.

Examples:

- UPTREND + confirmed close below controlling HL → `TRANSITION`.
- DOWNTREND + confirmed close above controlling LH → `TRANSITION`.

The invalidated historical structure remains preserved historically but becomes structurally inactive and non-controlling.

A new transition episode is created when a later established replacement regime is itself invalidated.

Old invalidated structure is not silently revived as the current structure.

## 17. RANGE

RANGE is a structural regime, not the complement of UPTREND/DOWNTREND.

A valid range requires:

1. alternating meaningful swing structure;
2. an upper resistance boundary zone;
3. a lower support boundary zone;
4. later meaningful swing reactions to those boundaries;
5. the boundary reactions occur as an alternating sequence between the upper and lower boundaries;
6. no sustained directional progression sufficient to establish UPTREND or DOWNTREND.

### 17.1 Boundary reaction

A later meaningful swing is a reaction to an existing boundary when its canonical swing zone overlaps that boundary zone.

- Meaningful High zone overlapping upper boundary → upper-boundary reaction.
- Meaningful Low zone overlapping lower boundary → lower-boundary reaction.
- No overlap → no reaction to that boundary.

No numerical proximity tolerance is introduced.

### 17.2 Range establishment

The alternating reaction sequence may begin from either boundary.

The engine must observe actual alternating structural reactions between the upper and lower boundaries before establishing RANGE.

Non-directional structure that does not satisfy the RANGE conditions remains `UNCLEAR`.

### 17.3 Range breakout

A range breakout is recorded as a structural event/subtype of the existing transition process, such as `RANGE_BREAKOUT_UP` or `RANGE_BREAKOUT_DOWN`.

A range breakout alone does not establish UPTREND or DOWNTREND.

A failed boundary penetration that returns into the range does not automatically change RANGE; it is recorded as a structural observation/event unless the established transition rules are satisfied.

## 18. UNCLEAR

`UNCLEAR` is the required fallback when the evidence is insufficient, ambiguous, internally conflicting, or does not validly establish:

- UPTREND;
- DOWNTREND;
- RANGE; or
- a post-invalidation TRANSITION state.

While UNCLEAR, the engine provides no valid H1 directional bias.

UNCLEAR may transition directly to the first valid established regime. TRANSITION is reserved for structural change after an established regime.

## 19. Regime persistence and conflict handling

An established regime persists while its defining conditions remain valid.

Isolated opposing evidence does not replace an established regime.

If both trend and range evidence appear:

- an established regime remains until its defining conditions are invalidated/changed;
- during initial establishment, evidence that cannot validly distinguish a regime remains UNCLEAR.

No additional precedence regime is introduced.

## 20. Evaluation output

The engine returns `MarketStructureState` containing at minimum:

- current regime;
- strategy/structure version;
- meaningful highs;
- meaningful lows;
- controlling level/swing where applicable;
- structural events explaining state transitions;
- evaluation timestamp/cutoff.

The output must preserve sufficient evidence to explain why the current regime was reached without reconstructing decisions from future data.

## 21. Deterministic invariants

The implementation must enforce these invariants:

1. Candidate windows always contain exactly three H1 candles.
2. Dual candidates produce neither a high nor a low candidate.
3. An unconfirmed candidate may be replaced by a newer competing candidate.
4. Once an opposing swing forms, candidate identity is immutable.
5. Exactly one active opposing swing exists for the active candidate.
6. Only a more extreme opposing candidate replaces the active opposing swing.
7. Confirmation requires a completed H1 close beyond the opposing swing extreme.
8. Confirmation does not imply meaningfulness.
9. Meaningfulness follows active structural-chain participation.
10. Swing zones are immutable.
11. Equality is zone overlap.
12. Equal swings never become controlling.
13. Regime classification uses the active structural chain only.
14. Directional invalidation requires a completed H1 close beyond the controlling structural level.
15. Invalidation does not automatically reverse the regime.
16. RANGE is not implemented as `not UPTREND and not DOWNTREND`.
17. RANGE requires alternating boundary reactions.
18. Future candles after `evaluation_cutoff` cannot influence the result.
19. Historical structural evidence remains auditable even when it becomes inactive.
20. The engine must not introduce undocumented numerical thresholds.

## 22. Explicit non-goals

MS-0.1A does not define:

- M15 CP-1/CP-2 confirmation;
- CP-2 execution-aware SL buffer;
- key-level source detection beyond structural information needed by H1 range state;
- risk percentage selection;
- session timezone/value definitions;
- trade/loss counting semantics;
- broker execution;
- AI/ML prediction or interpretation;
- live trading authorization.

Those remain separate milestones or explicitly unresolved decisions.

## 23. Acceptance criteria

MS-0.1A implementation is acceptable only if tests demonstrate at least:

1. Correct three-candle candidate high/low detection.
2. Correct dual-candidate rejection.
3. Correct candidate replacement.
4. Correct opposing-swing formation and dynamic extreme replacement.
5. Correct candidate immutability after opposing swing formation.
6. Correct confirmation only after completed H1 close beyond the opposing extreme.
7. Correct separation of confirmed and meaningful swings.
8. Correct active-chain construction and historical preservation.
9. Correct HH/HL/LH/LL/equality classification.
10. Correct controlling-swing updates.
11. Correct UPTREND establishment and persistence.
12. Correct DOWNTREND establishment and persistence.
13. Correct H1 close-based invalidation and TRANSITION.
14. Correct RANGE establishment through alternating boundary reactions.
15. Correct zone-overlap reaction detection.
16. Correct UNCLEAR fallback.
17. Correct regime persistence under isolated opposing evidence.
18. Correct no-lookahead behavior at different evaluation cutoffs.
19. Deterministic replay: identical inputs and cutoff produce identical state and structural events.
20. Evidence sufficient to explain every regime transition.

## 24. Remaining specification gate

One item must remain explicitly unresolved before implementation if the handbook does not already define it elsewhere: the deterministic method for selecting the **initial upper and lower candidate boundary zones** when RANGE is first being established.

The implementation must not invent a boundary-selection heuristic. Until that rule is explicitly locked, RANGE establishment must remain blocked at that boundary-selection step rather than silently applying an arbitrary first-high/first-low rule.
