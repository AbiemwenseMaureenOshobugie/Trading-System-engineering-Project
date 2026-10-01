# MS-0.8 — Noise Computation Specification

## Status

Locked and implementation-ready.

This specification defines deterministic H1 wick-based Noise computation for the execution-aware stop-loss buffer. It does not modify strategy confirmation, Risk Engine, Governance, Decision, or Execution semantics.

## N-01 — Directional wick formula

BUY:
- lower_wick = min(Open, Close) - Low
- Noise = mean(lower_wick)

SELL:
- upper_wick = High - max(Open, Close)
- Noise = mean(upper_wick)

All calculations use exact decimal arithmetic.

## N-02 — Timeframe

Noise is computed from H1 candles only. Non-H1 candles are not qualifying observations.

## N-03 — Qualifying H1 candle window

The qualifying window consists of completed H1 candles strictly after the latest meaningful H1 swing candle/event and through the latest completed H1 candle available to the calculator.

The latest meaningful swing is derived from the latest timestamp among the meaningful H1 highs and lows supplied by MarketStructureState.

The meaningful swing candle itself is excluded because the window is strictly after it.

No arbitrary candle-count, ATR, pip, percentage, or time-duration threshold is introduced.

## N-04 — Empty window

If there are no qualifying H1 candles, Noise = 0.

This includes the case where no meaningful H1 swing exists.

## Determinism

For fixed direction, H1 candle sequence, and MarketStructureState, the calculator returns exactly the same Decimal result. Input candle ordering must not change the result.

## Ownership and boundaries

The Noise Calculator owns only qualifying-window selection, directional wick calculation, arithmetic mean, and empty-window handling.

It does not own H1 market-structure classification, meaningful-swing identification, strategy confirmation, stop-loss placement, risk percentage, position sizing, volatility adjustment, governance, or execution.

The Risk Engine continues to consume Noise through the existing RiskRequest.noise field.

## Interface boundary

The application layer exposes a dedicated NoiseCalculatorPort:

compute(candles, structure, direction) -> Decimal

The calculator is downstream of H1 Market Structure and upstream of Risk Request construction.

## Pipeline placement

H1 Market Structure -> Noise Calculator -> RiskRequest.noise -> Risk Engine -> Execution-aware Stop Loss

## Explicit non-changes

MS-0.8 does not change CP-1, CP-2, M15 confirmation, Key-Level detection, Risk Engine formulas, the fixed 1% risk rule, minimum 1:2 R:R, Governance, Decision, or Execution. It does not add volatility-based risk scaling.

## Version

MS-0.8
