# MS-0.31 — Real Historical Replay Wiring

Status: implementation candidate; CI and a bounded runtime replay are required before merge.

## Purpose

Connect the existing MS-0.11 replay harness to the already implemented ASTER
strategy, risk, governance, decision, paper-execution, exit, journal, and
analytics components. This is integration work, not a new strategy milestone.

## Historical input

HistoricalCSVAdapter loads completed OHLC candles from caller-supplied CSV
files. Required columns: timestamp_open,timestamp_close,open,high,low,close.
Optional columns: symbol,timeframe,volume. Timestamps must include a timezone.
CSV contents are fingerprinted with SHA-256 and retained in each candle's
source provenance. Duplicate candle-open timestamps and malformed records are
rejected. This adapter does not call Twelve Data or use the wall clock to decide
whether a historical candle is complete.

## Real strategy path

RealReplayPipeline invokes the existing H1 structure, Key-Level detection,
governing Key-Level selection, M15 confirmation, setup classification, Risk,
Governance, and Decision engines. Each call receives only candles whose close
timestamp is at or before the replay cutoff.

Spread, slippage, noise, volatility adjustment, and value per price unit are
explicit caller-supplied inputs. Session eligibility comes from the existing
MS-0.8 Session Policy Engine. Missing contract valuation or setup-level context
does not produce an executable candidate. The pipeline exposes an in-memory
trace of candidate, risk, governance, and decision outcomes for inspection.

## Execution and evaluation

compose_backtest_engine connects the pipeline to the existing MS-0.11 replay
harness, MS-0.7 paper entry execution, MS-0.10 exit manager and paper exit
execution, journal factory, and descriptive performance analytics. The replay
clock follows the historical cutoff so paper execution timestamps are not
taken from wall-clock time.

Paper entry fills use the signal entry price. Paper exit fills use the existing
exit instruction trigger price. These are deterministic paper assumptions, not
broker-fill claims.

## Boundaries

- No new entry, exit, risk, governance, or session rules.
- No Twelve Data wall-clock completion logic is reused for CSV history.
- No missing cost or contract input is silently defaulted.
- A passing unit-test suite is not evidence of profitability.
- Before interpreting performance, inspect data coverage, pipeline trace,
  ambiguity events, failed executions, and future-data violations.
