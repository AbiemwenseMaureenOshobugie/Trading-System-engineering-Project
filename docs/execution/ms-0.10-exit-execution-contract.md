# MS-0.10 — Exit Execution Contract

## Purpose
Defines deterministic exit instruction, authorization, lifecycle, paper-exit evidence, and journal evidence semantics. No new strategy, risk formula, governance rule, broker state, partial fills, retry, or reconciliation.

## EX-D10 — Exit instruction authority
Position / Exit Management creates exit instructions from an actual open position plus approved RiskResult geometry. Risk owns stop/target geometry, not open-position lifecycle.

## EX-D11 — ExitInstruction
Minimum fields:
- exit_instruction_id
- position_id
- decision_id
- symbol
- direction (original position direction)
- exit_type: STOP_LOSS or TARGET
- requested_quantity
- trigger_price
- created_timestamp
- source_reference

STOP_LOSS uses RiskResult.final_stop_loss. TARGET uses RiskResult.target_price. Actual fill price/timestamp, P&L, broker IDs, and slippage are execution evidence, not instruction fields.

## EX-D12 — Exit authorization
Authorization requires an actual open position, valid decision/entry provenance, approved exit type, trigger price matching RiskResult geometry, and quantity not exceeding the open position quantity. An exit does not rerun the entry Strategy → Risk → Governance → Decision cycle.

## EX-D13 — Lifecycle
CREATED → AUTHORIZED → SUBMITTED → FILLED, or SUBMITTED → FAILED. FILLED and FAILED are terminal. PARTIALLY_FILLED, CANCELLED, EXPIRED, BROKER_REJECTED, RETRYING, and RECONCILING are deferred.

## EX-D14 — Actual fill
Actual exit evidence contains exit_fill_id, exit_instruction_id, actual_exit_price, executed_quantity, and exit_execution_timestamp. Paper execution may deterministically set actual_exit_price equal to trigger_price; this is not a general execution rule.

## EX-D15 — Failed exit
FAILED contains failure reason/timestamp and no fill evidence. It does not complete the journal and leaves the position open. Retry/recovery/reconciliation are deferred.

## EX-D16 — Journal evidence
A completed journal entry requires actual entry and exit execution evidence linked by decision/position provenance. Journal must never substitute signal price, target price, or signal timestamp for actual execution evidence.

## MS-0.7 consistency
MS-0.7 entry execution remains Decision VALID + Risk AUTHORIZED + Governance AUTHORIZED → AUTHORIZED → SUBMITTED → FILLED/FAILED. MS-0.10 does not change it.

## MS-0.9 consistency
MS-0.9 already uses execution-aware entry/exit IDs, prices, timestamps, executed quantity, and realized P&L. MS-0.10 supplies the missing upstream exit-execution semantics without changing those fields.

## Authority
Risk = geometry. Position/Exit Management = exit instruction. Execution = submission/fill evidence. Journal = completed-trade record. Analytics = descriptive analysis.
