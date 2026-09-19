# ASTER — MS-0.4 Risk & Trade Qualification

## Status

**Implementation baseline:** MS-0.4  
**Risk rate:** fixed at 1%  
**Minimum reward-to-risk:** 2R  
**Execution:** no live execution authority in this milestone

## Purpose

MS-0.4 converts a strategy-qualified `DecisionCandidate` into a deterministic
risk result. It owns trade-risk qualification, execution-aware stop placement,
target feasibility, and position sizing. It does not detect setups, select the
governing Key Level, or override Governance.

## Risk Contract

The Risk Engine receives a `RiskRequest` containing:

- the strategy-qualified `DecisionCandidate`;
- active Key Levels with their preserved source zones;
- the governing setup Key-Level identity;
- account equity;
- spread;
- slippage;
- noise;
- volatility adjustment;
- monetary value per unit of price movement.

The last item is an explicit sizing input. MS-0.4 does not invent broker-specific
pip-value or contract-conversion rules.

## Fixed Risk

Risk is fixed at:

```
risk_rate = 0.01
risk_amount = account_equity × 0.01
```

No dynamic risk adjustment, volatility-based risk percentage, portfolio limit,
correlation limit, or AI risk adjustment is introduced.

## Structural Stop

The candidate supplies the structural stop determined upstream from the
applicable confirmation setup.

For CP-1:

- BUY structural SL = rejection candle Low.
- SELL structural SL = rejection candle High.

For CP-2:

- ordinary BUY structural SL = C1 Low;
- ordinary SELL structural SL = C1 High;
- sweep BUY structural SL = frozen Sweep Low;
- sweep SELL structural SL = frozen Sweep High.

MS-0.4 does not redefine those confirmation rules.

## Execution-Aware Buffer

The same execution-aware buffer is applied to CP-1 and CP-2:

```
buffer = spread + slippage + noise + volatility_adjustment
```

Final SL:

- BUY: `final_sl = structural_sl - buffer`
- SELL: `final_sl = structural_sl + buffer`

A non-positive stop distance rejects the candidate.

## Target Rule

**ASTER targets the nearest opposing source-zone boundary in the trade
direction. If that structural target provides at least 2R, it becomes TP. If it
provides less than 2R, the trade is rejected. If no opposing source-zone
boundary exists, TP defaults to exactly 2R.**

BUY:

1. Consider active Key Levels other than the governing setup Key Level.
2. Preserve every source zone exactly as supplied by MS-0.2.
3. Consider source-zone boundaries above Entry.
4. Select the boundary with the smallest positive distance from Entry.
5. Calculate candidate R:R.
6. If R:R >= 2.0, use that boundary as TP.
7. If R:R < 2.0, reject the trade.
8. If no qualifying opposing boundary exists, use `Entry + 2R`.

SELL:

1. Consider active Key Levels other than the governing setup Key Level.
2. Preserve every source zone exactly as supplied by MS-0.2.
3. Consider source-zone boundaries below Entry.
4. Select the boundary with the smallest positive distance from Entry.
5. Calculate candidate R:R.
6. If R:R >= 2.0, use that boundary as TP.
7. If R:R < 2.0, reject the trade.
8. If no qualifying opposing boundary exists, use `Entry - 2R`.

No source type is given priority. No union, intersection, midpoint, synthetic
zone, or generic level-strength score is created.

## Position Sizing

```
position_size =
    risk_amount / (stop_distance × value_per_price_unit)
```

MS-0.4 performs no broker-specific rounding or lot-step conversion.

## Qualification

A candidate is risk-authorized only when:

- structural stop exists;
- final stop is valid relative to Entry;
- target exists;
- target distance is positive;
- R:R is at least 2.0;
- fixed risk amount can be calculated;
- position size can be calculated.

Otherwise the result is `RISK_REJECTED` with a deterministic reason code.

## Architecture Boundary

```
Strategy / Confirmation
        ↓
DecisionCandidate
        ↓
RiskRequest
        ↓
RiskEngine
        ↓
RiskResult
        ↓
Governance
        ↓
Execution
```

The Risk Engine does not:

- detect CP-1 or CP-2;
- detect or consolidate Key Levels;
- select the governing setup Key Level;
- apply session restrictions;
- apply daily trade-count or loss-count rules;
- execute broker orders;
- use AI/ML to alter risk or qualification.

## Audit Requirements

A risk result must preserve:

- decision ID;
- requested and approved risk;
- Entry assumption;
- structural SL;
- final SL;
- TP;
- stop distance;
- target distance;
- R:R;
- monetary risk;
- position size;
- deterministic reason codes.

## Acceptance Tests

The implementation must verify:

1. fixed 1% risk;
2. CP-1/CP-2 execution-aware stop buffering;
3. nearest opposing source-zone boundary selection;
4. structural target accepted when R:R >= 2;
5. structural target rejected when R:R < 2;
6. exact 2R fallback when no opposing boundary exists;
7. governing setup Key Level excluded from target obstacles;
8. inactive Key Levels excluded;
9. invalid stop distance rejected;
10. deterministic position sizing.

