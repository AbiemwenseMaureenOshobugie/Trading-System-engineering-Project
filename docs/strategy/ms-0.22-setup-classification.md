# MS-0.22 — Setup Classification

## Status
Frozen and implemented.

## Purpose
Convert an already-triggered MS-0.3 confirmation into a DecisionCandidate without reinterpreting confirmation semantics or calculating downstream risk/execution fields.

## Input contract
SetupClassifierPort.classify() receives a sequence of ConfirmationSequence values.

Only confirmations with signal_status == SIGNAL_TRIGGERED are eligible.

A triggered confirmation must contain:
- symbol
- signal_timestamp
- signal_entry_price

## Candidate mapping
| Candidate field | Source |
|---|---|
| decision_id | deterministic SHA-256 identity |
| strategy_version | MS-0.22 |
| symbol | confirmation symbol |
| direction | confirmation direction |
| setup_type | confirmation type |
| setup_id | confirmation setup identity |
| signal_timestamp | confirmation trigger timestamp |
| signal_entry_price | confirmation trigger entry price |
| proposed_stop_loss | None |
| proposed_target | None |
| evidence_refs | structured references to confirmation, Key-Level, candles, and confirmation type |

## Decision identity
The deterministic identity is derived from the canonical tuple:

MS-0.22 | symbol | direction | setup_type | setup_id | signal_timestamp | signal_entry_price

The digest is SHA-256 and is prefixed with DEC-.

The classifier uses no UUID, current time, randomness, process-local counter, or mutable state.

## Evidence
Evidence is carried forward only. The classifier does not reinterpret candles or create new trading evidence.

## Downstream ownership
The classifier does not calculate:
- stop loss
- target
- risk/reward
- position size
- governance eligibility
- execution authorization

Those remain downstream responsibilities.

## Boundary
MS-0.3 owns trigger semantics. MS-0.22 owns only conversion of an already-triggered confirmation into a candidate.
