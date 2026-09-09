# Component Architecture

## 1. Architectural objective

The component architecture converts Strategy Specification v0.1.0 into isolated responsibilities with clear interfaces. Components should be independently testable while remaining simple enough for the initial local implementation.

## 2. Components

### Market Data Adapter
Obtains H1 and M15 OHLC data from the configured market-data source. MT5 integration is an adapter boundary, not a strategy dependency.

### Data Validation
Checks timestamps, ordering, missing candles, duplicates, invalid OHLC relationships, symbol identity, and timeframe integrity before strategy logic consumes data.

### Normalization
Converts validated provider data into the internal candle representation and standardizes symbol/time conventions required by the engine.

### Feature Engineering
Derives deterministic observations needed by the strategy, such as candle relationships, swing candidates, structural levels, and confirmation measurements. It must not leak future information into historical decisions.

### H1 Market Structure Engine
Classifies H1 structure into exactly one of the approved regimes: UPTREND, DOWNTREND, RANGE, TRANSITION, or UNCLEAR. It reconstructs meaningful swings rather than treating every local fluctuation as structural evidence.

### Key-Level Engine
Detects approved key-level sources: Validated Swing, Range Boundary, Breakout Level, and Role Reversal as a state transition of an existing level. It owns level identity, deduplication, and level state.

### M15 Confirmation Engine
Evaluates CP-1 and CP-2 sequences. It maintains setup state across candles and invalidates sequences according to frozen rules rather than creating ad-hoc patterns.

### Setup Classifier
Converts qualifying strategy events into a structured decision candidate, including setup type, governing key level, direction, signal timing, and evidence.

### Risk Engine
Calculates permitted risk and trade geometry independently of setup detection. It enforces the frozen risk constraints, minimum 1:2 R:R, and the applicable entry/SL/target requirements.

### Governance Engine
Applies non-negotiable controls such as maximum two trades per day, stop after two losses, approved instruments/session, and other explicitly frozen governance rules. Governance can block an otherwise valid strategy signal.

### Decision Engine
Combines strategy qualification, risk authorization, and governance authorization into a final system outcome such as VALID, WAIT, or BLOCKED, with distinct risk and governance failure reasons.

### Execution Gateway
Future boundary between an authorized decision and MT5/broker order submission. It must never accept an unapproved strategy candidate directly.

### Audit / Journal
Persists input observations, strategy version, rule evaluations, decisions, risk results, governance results, signals, execution records, and post-trade outcomes.

### Analytics / Backtest Engine
Replays historical data through the same deterministic logic and produces performance metrics while enforcing chronological integrity and avoiding look-ahead bias.

### Explanation Layer
Produces human-readable explanations from recorded deterministic evidence. An LLM may assist here later, but explanation must not mutate the authoritative decision state.

## 3. Dependency direction

```text
Adapters → Validation → Normalization → Features
                                      ↓
                              Strategy Engines
                                      ↓
                              Setup Classifier
                                      ↓
                         Risk Engine + Governance
                                      ↓
                              Decision Engine
                                      ↓
                           Execution Gateway
                                      ↓
                                   Broker
```

Audit/journal receives records from each material decision boundary. Analytics consumes historical records and replay outputs; it does not alter live decision state.

## 4. Separation of concerns

Strategy determines **whether methodology conditions are satisfied**. Risk determines **whether the proposed trade is acceptable from the defined risk perspective**. Governance determines **whether the action is permitted at all**. Execution determines **whether and how an authorized instruction reaches the broker**.

No component should silently absorb another component's authority.
