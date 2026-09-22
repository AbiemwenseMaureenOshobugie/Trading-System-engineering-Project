# ASTER — MS-0.3 M15 Confirmation Specification

## Status

**Milestone:** MS-0.3  
**Layer:** M15 Confirmation  
**Purpose:** deterministic confirmation of an already-established H1 thesis at an already-selected governing Key Level  
**Execution:** no broker/live execution authority

## 1. Objective

MS-0.3 defines ASTER's deterministic M15 confirmation layer.

MS-0.3 answers:

> Does the M15 price action provide the required confirmation for the established H1 thesis at the governing Key Level?

MS-0.3 does not redefine H1 market structure, detect Key Levels, calculate risk, apply governance, or execute trades.

The governing Key Level is supplied to the confirmation engine by downstream selection logic. MS-0.3 does not choose among Key Levels.

## 2. Inputs

The confirmation layer consumes:

- completed M15 candles;
- the established H1 structure/thesis;
- exactly one already-selected governing `setup_key_level`.

The confirmation engine must not create a second Key-Level selection algorithm.

## 3. Confirmation Paths

MS-0.3 supports two confirmation paths:

1. **CP-1 — Breakout / Pullback / Rejection Confirmation**
2. **CP-2 — Key-Level Rejection Confirmation**

Both paths produce deterministic confirmation sequences that can become strategy-qualified candidates for downstream Risk and Governance processing.

## 4. CP-1 — Micro-Breakout Confirmation

### 4.1 Canonical sequence

CP-1 is:

> **Micro-breakout → return to broken micro-level → rejection → M15 structure alignment → final trigger.**

The sequence is complete only when all required conditions occur in order.

### 4.2 Micro-breakout

A micro-breakout is a completed M15 candle close beyond the most recent confirmed M15 opposing swing.

For a bullish H1 thesis:

- the completed M15 candle must close above the most recent confirmed M15 swing high;
- that swing high becomes the broken micro-level.

For a bearish H1 thesis:

- the completed M15 candle must close below the most recent confirmed M15 swing low;
- that swing low becomes the broken micro-level.

No arbitrary pip, percentage, ATR, volatility, or indicator threshold is introduced.

### 4.3 M15 pullback/retest

A valid M15 pullback/retest is:

> **A return of price to the broken micro-level followed by a rejection at that level.**

No separate numerical retest tolerance is introduced.

### 4.4 Rejection

The rejection must satisfy the already-defined M15 rejection semantics.

For BUY:

- lower wick > body;
- bullish body;
- close in the upper third of the candle.

For SELL:

- upper wick > body;
- bearish body;
- close in the lower third of the candle.

Body classification is qualitative:

- doji: invalid;
- spinning/borderline candle: borderline and not accepted as a directional rejection;
- normal directional body: valid;
- marubozu: valid.

### 4.5 M15 structure alignment

M15 structure alignment occurs when a **confirmed M15 swing** establishes an HH/HL or LH/LL relationship against the most recent confirmed M15 swing of the same type, with the relationship evaluated in the direction of the established H1 thesis.

For bullish H1:

- confirmed M15 High > most recent confirmed M15 High → HH alignment;
- confirmed M15 Low > most recent confirmed M15 Low → HL alignment.

For bearish H1:

- confirmed M15 High < most recent confirmed M15 High → LH alignment;
- confirmed M15 Low < most recent confirmed M15 Low → LL alignment.

MS-0.3 does not require both an HH/HL relationship simultaneously. One qualifying directional structural relationship is sufficient for alignment.

M15 alignment does not require:

- a full M15 regime classification;
- H1 meaningfulness rules;
- M15 Key Levels;
- indicators;
- arbitrary candle-count thresholds;
- ATR/pip/percentage thresholds.

### 4.6 Final trigger

For BUY:

> The immediate next M15 candle after the rejection must close beyond the rejection high.

For SELL:

> The immediate next M15 candle after the rejection must close beyond the rejection low.

This immediate-next-candle close is the final CP-1 trigger and represents the required follow-through.

If the immediate next candle fails to satisfy the trigger:

- the original rejection expires;
- the sequence does not remain pending indefinitely;
- a fresh qualifying rejection is required where applicable.

## 5. M15 Swing Detection for MS-0.3

MS-0.3 uses a deterministic confirmed-candidate model for M15 structural relationships.

### 5.1 Candidate High

For three consecutive M15 candles:

- Middle High > Left High;
- Middle High > Right High;
- Middle Low > Right Low.

The middle candle is a candidate High.

### 5.2 Candidate Low

For three consecutive M15 candles:

- Middle Low < Left Low;
- Middle Low < Right Low;
- Middle High < Right High.

The middle candle is a candidate Low.

### 5.3 Confirmation

The third/right candle completes the three-candle candidate pattern and confirms the candidate.

No additional lookback, ATR, pip, percentage, or indicator threshold is introduced.

Nested candidates are retained where the deterministic candidate conditions independently qualify.

If the methodology encounters consecutive candidates of the same type, the latest qualifying candidate replaces the prior candidate used for the relevant confirmation relationship when required by the structural sequence.

A dual candidate that simultaneously qualifies as both High and Low is rejected.

## 6. CP-2 — Key-Level Rejection Confirmation

### 6.1 Canonical sequence

CP-2 begins at the already-selected governing Key Level.

The ordinary sequence is:

> **Approach governing Key Level → rejection → strong response → entry.**

The sweep sequence is:

> **Approach governing Key Level → sweep → return/rejection → strong response → entry.**

### 6.2 First qualifying rejection candle

C1 is the first M15 candle that qualifies as a rejection at the governing Key Level.

C1 does not have to be the first candle that interacts with the Key Level. It is the first candle satisfying the rejection conditions after the setup context reaches the governing level.

### 6.3 Ordinary rejection

BUY ordinary rejection:

- lower wick > body;
- bullish body;
- close in upper third.

SELL ordinary rejection:

- upper wick > body;
- bearish body;
- close in lower third.

Doji is invalid. Borderline spinning candles are not accepted as directional rejection. Normal directional bodies and marubozu bodies qualify.

### 6.4 Consecutive confirmation candles

The CP-2 ordinary sequence uses three consecutive M15 candles:

- C1 = qualifying rejection;
- C2 = immediate candle after C1;
- C3 = immediate candle after C2.

C2 must preserve the directional rejection context and must not introduce an adverse structural excursion that invalidates the sequence.

For BUY:

- C2 Close > C1 High;
- C3 Close > C1 High.

For SELL:

- C2 Close < C1 Low;
- C3 Close < C1 Low.

Additionally, C3 must provide the final directional continuation required by the sequence.

For BUY:

- C3 Close > C2 High.

For SELL:

- C3 Close < C2 Low.

If C3 fails the required confirmation, the current sequence is invalidated and a fresh qualifying rejection is required.

### 6.5 Sweep detection

For BUY:

- price must penetrate below the governing Key Level;
- Sweep Low is the lowest price reached during the penetration.

For SELL:

- price must penetrate above the governing Key Level;
- Sweep High is the highest price reached during the penetration.

### 6.6 Sweep extreme lifecycle

Before C1 closes, the sweep extreme remains mutable.

At C1 close:

- the extreme is frozen;
- the frozen value becomes immutable for that sequence.

After C1 closes, a more-extreme price does not modify the existing Sweep Low/Sweep High. It creates a new sweep event and therefore requires a new C1 sequence.

### 6.7 Sweep invalidation

For a BUY sweep sequence, a later C2/C3 price excursion that breaches the frozen Sweep Low invalidates the current sequence.

For a SELL sweep sequence, a later C2/C3 price excursion that breaches the frozen Sweep High invalidates the current sequence.

There is no salvage or adjustment of the existing sequence. A new sweep/fresh C1 is required.

### 6.8 Sweep confirmation

For BUY:

- C2 Close > Sweep Low;
- C2 Close > C1 High;
- C3 Close > C1 High;
- C3 Close > C2 High.

For SELL:

- C2 Close < Sweep High;
- C2 Close < C1 Low;
- C3 Close < C1 Low;
- C3 Close < C2 Low.

### 6.9 Governing Key Level

Every CP-2 sequence has exactly one `setup_key_level`.

Other Key Levels do not automatically invalidate or modify the confirmation sequence.

Other Key Levels may later matter to:

- target feasibility;
- reward-to-risk;
- execution considerations.

Those concerns belong to downstream Risk/Execution logic.

## 7. H1 Invalidation Priority

A pending M15 confirmation is cancelled if a confirmed H1 invalidation occurs before entry.

H1 invalidation is evaluated only after the relevant H1 candle closes.

An intrabar H1 wick does not cancel a pending M15 confirmation.

If the M15 confirmation produces an entry before the H1 candle closes, a later H1 invalidation does not retroactively cancel that already-generated entry.

Therefore:

> **H1 invalidation has priority over a pending M15 setup, but does not retroactively alter an already-triggered entry.**

## 8. Pending Confirmation

MS-0.3 uses a minimal pending-confirmation representation.

There is at most one active pending confirmation per direction.

A pending confirmation may represent CP-1 or CP-2 and records only the context required to evaluate its next condition.

Its lifecycle is:

- `PENDING`;
- `TRIGGERED`;
- `EXPIRED`;
- `INVALIDATED`, where applicable.

The pending object does not introduce:

- confidence scores;
- strength thresholds;
- arbitrary timeout windows;
- minimum candle counts beyond the explicit confirmation sequences;
- additional confirmation conditions.

A failed/expired sequence requires a fresh qualifying rejection where the methodology requires one.

## 9. Signal and Execution Boundary

MS-0.3 produces a **signal**, not a broker execution.

For CP-1:

- signal entry price = qualifying trigger-candle close.

For CP-2:

- signal entry price = C3 close.

Actual broker execution is downstream and is represented separately from the signal.

The system must preserve the distinction between:

- Signal;
- Order;
- Position/Fill.

## 10. Non-Goals

MS-0.3 does not define:

- H1 market-structure detection;
- H1 regime classification;
- H1 meaningful-swing rules;
- Key-Level detection;
- governing Key-Level selection;
- Risk qualification;
- stop-loss calculation;
- target calculation;
- reward-to-risk qualification;
- Governance authorization;
- broker execution;
- live execution mechanics;
- AI/ML prediction or interpretation.

## 11. Deterministic Invariants

1. M15 confirmation operates in the direction of an established H1 thesis.
2. CP-1 requires micro-breakout → retest → rejection → M15 alignment → immediate-next-candle trigger.
3. CP-1 micro-breakout is confirmed by an M15 close beyond the most recent confirmed opposing M15 swing.
4. The broken micro-level is the swing level broken by that breakout.
5. A CP-1 rejection must occur at the broken micro-level.
6. CP-1 final trigger is the immediate next M15 candle close beyond the rejection extreme.
7. A failed immediate-next-candle trigger expires the original rejection.
8. CP-2 uses exactly one governing setup Key Level.
9. C1 is the first qualifying rejection at the governing Key Level, not necessarily the first interaction.
10. CP-2 ordinary confirmation uses consecutive C1/C2/C3 candles.
11. CP-2 sweep extremes evolve until C1 closes and then become immutable.
12. A post-C1 breach beyond a frozen sweep extreme invalidates the current sweep sequence.
13. CP-2 sweep confirmation uses the frozen extreme plus C1/C2/C3 directional closes.
14. H1 invalidation cancels pending M15 confirmation before entry.
15. H1 invalidation does not retroactively cancel an already-triggered entry.
16. M15 confirmation does not perform risk or governance authorization.
17. Identical approved inputs produce identical confirmation results.
18. No undocumented numerical tolerance is introduced.
19. No indicator-based confirmation is introduced.
20. No AI/ML component may override deterministic confirmation rules.

## 12. Implementation Gate

MS-0.3 methodology decisions M15-01 through M15-07 are closed.

Implementation must preserve the separation:

```
H1 Structure
    ↓
Key-Level Detection
    ↓
Governing Key-Level Selection
    ↓
M15 Confirmation
    ↓
DecisionCandidate
    ↓
Risk
    ↓
Governance
    ↓
Decision
    ↓
Execution
```

The MS-0.3 specification is the canonical documentation contract for the confirmation implementation and its tests.
