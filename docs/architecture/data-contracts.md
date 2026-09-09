# Data Contracts

## 1. Purpose

Data contracts define the minimum shape and semantic ownership of information exchanged between components. They are intentionally implementation-neutral at this milestone; concrete Python models and serialization formats will be defined during implementation.

## 2. Market Candle

Represents one completed OHLC candle.

Required conceptual fields:

- `symbol`
- `timeframe`
- `timestamp_open`
- `timestamp_close`
- `open`
- `high`
- `low`
- `close`
- `volume` when supplied by the data source
- `source`

Validation invariants include `high >= max(open, close)`, `low <= min(open, close)`, valid timestamp ordering, and consistent timeframe identity.

## 3. Market Structure State

Represents the H1 structural classification and its evidence.

Conceptual fields:

- `regime`
- `structure_version`
- meaningful highs/lows used as evidence
- controlling structural level where applicable
- structural events
- evaluation timestamp

`regime` must be one of `UPTREND`, `DOWNTREND`, `RANGE`, `TRANSITION`, `UNCLEAR`.

## 4. Key Level

Represents one governing structural price zone.

Conceptual fields:

- `key_level_id`
- `source_type`
- `zone_definition`
- `role`
- `created_at`
- `updated_at`
- supporting structural evidence
- state/history

Approved source types for v0.1.0 are Validated Swing, Range Boundary, Breakout Level, and Role Reversal as a role/state transition.

## 5. Confirmation Sequence

Represents an active or completed CP-1 or CP-2 process.

Conceptual fields:

- `setup_id`
- `confirmation_type`
- `direction`
- `setup_key_level`
- `state`
- candle references used by the sequence
- controlling extreme where applicable
- signal status
- invalidation reason when applicable

For CP-2, the governing key level is exactly one key level. Other detected levels do not silently redefine the active sequence.

## 6. Decision Candidate

Represents a strategy-qualified candidate before risk/governance authorization.

Conceptual fields:

- `decision_id`
- `strategy_version`
- `symbol`
- `direction`
- `setup_type`
- `setup_id`
- `signal_timestamp`
- `signal_entry_price`
- proposed stop-loss and target information
- evidence references

Signal entry is immutable and must not be overwritten by broker fill information.

## 7. Risk Result

Represents the independent Risk Engine outcome.

Conceptual fields:

- `decision_id`
- requested risk
- approved risk
- position size
- entry assumption
- stop distance
- target distance
- R:R
- status: `RISK_AUTHORIZED` or `RISK_REJECTED`
- reason codes

The exact CP-2 execution-aware SL buffer algorithm remains pending and must not be invented at this stage.

## 8. Governance Result

Represents the independent Governance Engine outcome.

Conceptual fields:

- `decision_id`
- instrument/session eligibility
- daily trade count
- daily loss-count state
- governance checks
- status: `GOVERNANCE_AUTHORIZED` or `GOVERNANCE_BLOCKED`
- reason codes

## 9. Execution Record

Represents actual broker interaction separately from strategy signal.

Conceptual fields:

- `decision_id`
- `order_submission_timestamp`
- broker order ID
- requested order details
- execution timestamp
- `execution_entry_price`
- executed quantity
- slippage
- broker status

## 10. Audit Record

Every material decision boundary should be traceable through:

`data → features → structure → key level → confirmation → decision → risk → governance → signal → execution → outcome`

Each record must identify the relevant strategy/specification version so historical decisions remain interpretable after future changes.
