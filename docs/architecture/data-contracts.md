# Data Contracts

## 1. Purpose

Data contracts define the minimum shape and semantic ownership of information exchanged between components. MS-0.2C converts these contracts into typed Python domain models without adding trading behavior.

The canonical models live under `src/trading_system/domain/`. They are immutable dataclass snapshots so later components can exchange explicit state without silently mutating prior decision evidence.

## 2. Market Candle

Python model: `MarketCandle`

Fields:

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

Implemented invariants:

- `timestamp_open < timestamp_close`
- timestamps are timezone-aware
- `high >= max(open, close)`
- `low <= min(open, close)`

The model does not impose a specific broker or provider convention beyond these canonical invariants.

## 3. Market Structure State

Python model: `MarketStructureState`

Fields:

- `regime`
- `structure_version`
- meaningful highs/lows represented by `SwingPoint`
- `controlling_level` where applicable
- `structural_events`
- `evaluated_at`

`regime` is restricted to the approved states: `UPTREND`, `DOWNTREND`, `RANGE`, `TRANSITION`, `UNCLEAR`.

`SwingPoint` records a timestamp, price, and whether the structural point is a `HIGH` or `LOW`. It does not determine whether a point is meaningful; that remains the responsibility of the Market Structure Engine.

## 4. Key Level

Python model: `KeyLevel`

Fields:

- `key_level_id`
- `source_type`
- `zone_definition`
- `role`
- `created_at`
- `updated_at`
- `evidence_refs`
- `state_history`

`PriceZone` represents the level as an interval with `lower` and `upper` bounds. It does not prescribe a numerical zone-width calculation.

Approved source types for v0.1.0 are `VALIDATED_SWING`, `RANGE_BOUNDARY`, `BREAKOUT_LEVEL`, and `ROLE_REVERSAL` as a role/state transition.

## 5. Confirmation Sequence

Python model: `ConfirmationSequence`

Fields:

- `setup_id`
- `confirmation_type`
- `direction`
- `setup_key_level`
- `state`
- `candle_refs`
- `controlling_extreme` where applicable
- `signal_status`
- `invalidation_reason` where applicable

`confirmation_type` is restricted to `CP-1` and `CP-2`.

The model deliberately keeps `state` and `signal_status` as explicit strings at this milestone because the methodology defines sequence behavior but does not yet require a universal domain enum for every intermediate lifecycle label. That decision avoids inventing additional state semantics.

For CP-2, `setup_key_level` identifies exactly one governing key level. Other detected levels do not silently redefine the active sequence.

## 6. Decision Candidate

Python model: `DecisionCandidate`

Fields:

- `decision_id`
- `strategy_version`
- `symbol`
- `direction`
- `setup_type`
- `setup_id`
- `signal_timestamp`
- `signal_entry_price`
- proposed stop-loss and target information
- `evidence_refs`

Signal entry is immutable and must not be overwritten by broker fill information.

## 7. Risk Result

Python model: `RiskResult`

Fields:

- `decision_id`
- requested risk
- approved risk
- position size
- entry assumption
- stop distance
- target distance
- R:R
- `status`
- reason codes

`status` is restricted to `RISK_AUTHORIZED` or `RISK_REJECTED`.

The exact CP-2 execution-aware SL buffer algorithm remains pending and is intentionally not encoded here.

## 8. Governance Result

Python model: `GovernanceResult`

Fields:

- `decision_id`
- instrument/session eligibility
- daily trade count
- daily loss-count state
- governance checks
- `status`
- reason codes

`status` is restricted to `GOVERNANCE_AUTHORIZED` or `GOVERNANCE_BLOCKED`.

The model records governance outcomes; it does not itself implement the maximum-trades, loss-stop, instrument, or session rules.

## 9. Execution Record

Python model: `ExecutionRecord`

Fields:

- `decision_id`
- `order_submission_timestamp`
- broker order ID
- requested order details
- execution timestamp
- `execution_entry_price`
- executed quantity
- slippage
- broker status

Execution remains separate from the strategy signal. A broker fill must not overwrite `signal_entry_price` or `signal_timestamp` in a `DecisionCandidate`.

## 10. Audit Record

Python model: `AuditRecord`

Fields:

- `audit_id`
- `timestamp`
- `event_type`
- `strategy_version`
- optional `decision_id`
- references to the recorded evidence/payloads
- optional outcome

Every material decision boundary should remain traceable through:

`data → features → structure → key level → confirmation → decision → risk → governance → signal → execution → outcome`

## 11. Domain-model boundaries

The domain package owns representation and basic data invariants. It does **not** own:

- market-structure classification logic;
- key-level detection logic;
- CP-1 or CP-2 qualification logic;
- risk calculations;
- governance decisions;
- broker order submission;
- AI/ML interpretation.

Those responsibilities remain in their architectural components. This keeps the domain model canonical without turning it into a hidden strategy engine.
