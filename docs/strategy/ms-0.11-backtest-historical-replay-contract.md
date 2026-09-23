# MS-0.11 — Backtest / Historical Replay Contract

**Status:** Frozen / Canonical  
**Baseline:** `9ddde6b8d07cc879a28e68a28074d7c0646e7524`  
**Purpose:** Define the deterministic historical replay boundary and backtest contract without introducing a second trading engine.

## 1. Purpose

MS-0.11 defines ASTER's historical replay and backtesting contract.

The backtest framework is a replay harness around the existing deterministic ASTER pipeline.

It does not implement a second version of:

- H1 market structure
- Key-Level detection
- M15 confirmation
- setup classification
- risk calculation
- governance
- session policy
- decision precedence
- execution-state rules
- position/exit rules

Those responsibilities remain owned by the existing deterministic components.

The backtest framework is responsible for:

- chronological historical replay;
- explicit historical-information cutoffs;
- orchestration of existing ASTER components;
- replay account and position state;
- historical execution-event resolution;
- preservation of pending strategy and active exit state;
- production of a deterministic, auditable backtest result.

## 2. Locked Decisions

| Decision | Locked choice |
|---|---|
| BT-D01 | A — Completed-candle chronological replay |
| BT-D02 | A — Thin sequential orchestrator |
| BT-D03 | C — Evidence-first fill resolution; no fabricated intrabar ordering |
| BT-D04 | A — Explicit replay account + multi-position state |
| BT-D05 | A — Persist existing pending confirmations and active exit instructions; no new pending-order semantics |
| BT-D06 | A — Deterministic typed BacktestResult with performance + audit/validation evidence |

## 3. BT-D01 — Historical Replay Boundary

### 3.1 Decision

ASTER replays historical market data chronologically using completed historical candles as the fundamental replay boundary.

At each replay point:

1. advance to the next completed historical candle;
2. establish an explicit evaluation cutoff at that candle's close;
3. expose only historical information whose timestamp is less than or equal to that cutoff to strategy evaluation;
4. invoke the existing deterministic ASTER pipeline;
5. process execution events that become objectively valid at that historical point;
6. update replay account, positions, journal, and audit state;
7. advance to the next historical replay point.

### 3.2 Information cutoff

For replay cutoff T:

> Every strategy input timestamp must be ≤ T.

No strategy component may receive information whose timestamp is later than T.

This includes market candles, structural evidence, confirmation evidence, Key-Level evidence, execution information, account state, position state, and journal state.

### 3.3 Candle close versus execution timing

The candle close establishes the information boundary. It does not imply that every execution occurs at the candle close. Actual historical execution timing is governed by BT-D03.

## 4. BT-D02 — Backtest Orchestration

### 4.1 Decision

MS-0.11 uses a thin sequential orchestrator coordinating existing ASTER components in chronological order.

```text
Historical Data
      ↓
Replay Cutoff
      ↓
Existing Strategy Components
      ↓
Existing Risk
      ↓
Existing Session / Governance
      ↓
Existing Decision
      ↓
Existing Execution
      ↓
Existing Position / Journal
      ↓
Existing Performance Analytics
```

### 4.2 Responsibilities

The orchestrator may advance replay time, construct replay-scoped inputs, invoke existing components, carry deterministic state, submit authorized execution requests, process objectively established execution events, update replay account and positions, pass completed journal evidence to analytics, and collect audit/validation evidence.

### 4.3 Prohibited responsibilities

The orchestrator must not implement H1/M15 structure rules, Key-Level rules, confirmation rules, setup classification, risk formulas, governance/session rules, decision precedence, exit geometry, or execution-state transitions.

The following architecture is prohibited:

```python
BacktestEngine.calculate_market_structure(...)
BacktestEngine.calculate_risk(...)
BacktestEngine.check_governance(...)
```

> Backtest = replay orchestration + historical state  
> Backtest ≠ second implementation of ASTER

## 5. BT-D03 — Historical Execution and Fill Resolution

### 5.1 Decision

Historical execution must be resolved from available evidence. ASTER must never fabricate intrabar ordering that the historical data cannot establish.

### 5.2 Entry

A qualifying deterministic decision produces an entry execution according to the existing execution contract.

```text
DecisionCandidate.signal_entry_price
                ≠
actual execution evidence
```

The values may be equal when the selected execution mode explicitly defines a fill at the requested price.

### 5.3 Exit instructions

Existing Risk/Position semantics provide exit instructions such as:

```text
RiskResult.final_stop_loss → STOP_LOSS instruction
RiskResult.target_price     → TARGET instruction
```

These are instructions/geometry, not completed execution evidence. A completed exit exists only when historical execution evidence establishes that an exit occurred.

### 5.4 Intrabar ambiguity

If one OHLC candle contains both STOP LOSS and TARGET, but available data is only OHLC, ordering may be unknowable.

ASTER must not assume STOP first or TARGET first without supporting evidence.

The result is:

```text
AMBIGUOUS_EXIT_ORDERING
```

### 5.5 Finer-grained evidence

If finer historical data is available, it may establish objective ordering.

```text
M15 candle
    ↓
M1 historical data
    ↓
chronological M1 replay
    ↓
objectively established first event
```

If evidence establishes stop first, stop is the historical exit. If it establishes target first, target is the historical exit. If ordering remains unknowable, it remains ambiguous.

> Unknown historical information remains unknown.

## 6. BT-D04 — Replay Account and Position State

### 6.1 Decision

The replay uses an explicit account state capable of holding multiple simultaneous positions.

```text
BacktestAccountState
│
├── account_equity
├── realized_pnl
├── open_positions[]
├── completed_trades[]
├── daily_trade_count
├── daily_loss_count
└── replay_timestamp
```

### 6.2 Multiple positions

MS-0.11 does not introduce a one-position-at-a-time restriction.

Multiple positions may coexist when permitted by the existing ASTER Strategy, Risk, Governance, and Session components.

The backtester must not create a new simultaneous-position governance rule merely for implementation convenience.

### 6.3 Account updates

Account state is updated from actual completed execution evidence:

```text
Entry Fill → Open Position → Exit Fill → Realized P&L → Account State
```

MS-0.11 does not introduce a separate mark-to-market equity methodology.

## 7. BT-D05 — Pending Confirmations and Active Exit Instructions

### 7.1 Decision

The replay preserves deterministic state already existing within ASTER. It does not introduce new pending-order or lifecycle semantics.

### 7.2 Pending strategy confirmation

Existing MS-0.3 confirmation semantics are carried through replay:

```text
CP-1 / CP-2
      ↓
Pending Confirmation
      ↓
Next Historical Point
      ↓
Triggered / Expired / Invalidated
```

The replay must not introduce arbitrary timeouts, additional confirmation candles, confidence scores, new expiry rules, or new setup states.

### 7.3 Active exit instructions

Once a position exists, its active exit instructions remain actionable until the position is closed.

```text
Position OPEN
     │
     ├── STOP_LOSS active
     │
     └── TARGET active
             │
             ▼
       objectively established exit event
             │
             ▼
       Position CLOSED
```

Once the position closes, its remaining exit instruction is no longer actionable.

MS-0.11 does not introduce a new CANCELLED execution state.

### 7.4 Ambiguous exit ordering

If historical evidence cannot establish which active exit occurred first, BT-D03 applies and the completed trade outcome must not be fabricated.

## 8. BT-D06 — Backtest Result Contract

### 8.1 Decision

MS-0.11 produces a typed deterministic BacktestResult preserving sufficient evidence to explain the replay.

It must not collapse the run into only profit or trades.

### 8.2 Result categories

**Run identity**
- backtest_id
- backtest_version
- strategy_versions
- start_timestamp
- end_timestamp

**Replay configuration**
- symbol_universe
- timeframes
- historical_data_source
- historical_data_version
- initial_account_equity
- replay_mode

**Execution evidence**
- entry_executions
- exit_executions
- completed_positions
- failed_executions
- ambiguous_execution_events

**Journal**

Completed trades must satisfy the existing journal contract. The backtester does not create a competing journal schema.

**Performance**

Completed journal evidence is passed to the existing analytics layer:

```text
Completed Journal → Existing Performance Analytics → PerformanceSnapshot
```

MS-0.11 does not implement a competing performance-calculation model.

**Decision statistics**

The result may contain descriptive counts including:

- strategy_candidates
- valid_decisions
- wait_decisions
- risk_rejections
- governance_blocks
- executed_entries
- completed_trades
- failed_executions
- ambiguous_executions

These are observational statistics only and do not alter trading decisions.

**Validation evidence**

The result must preserve:

- future_data_violations
- ordering_violations
- ambiguous_execution_events

The implementation may use more precise typed structures while preserving these semantics.

## 9. Core Invariants

### INV-01 — No look-ahead

For replay cutoff T:

> Every strategy input timestamp ≤ T.

No exception is permitted.

### INV-02 — One trading engine

> Backtest = orchestration + historical state  
> Backtest ≠ second trading engine

### INV-03 — Signal and execution remain separate

```text
signal_entry_price ≠ actual execution price
```

unless the selected execution mode explicitly establishes equality.

### INV-04 — Risk geometry is not execution evidence

```text
RiskResult.final_stop_loss
RiskResult.target_price
```

are exit instructions and do not by themselves constitute completed exits.

### INV-05 — Unknown ordering remains unknown

If available historical evidence cannot establish which competing execution event occurred first, AMBIGUOUS_EXIT_ORDERING must be preserved.

### INV-06 — Journal requires completed evidence

A failed, unresolved, or ambiguous exit must not silently become a completed journal trade.

### INV-07 — Analytics remains downstream

```text
Journal → Analytics
```

Analytics must never become an input into Strategy, Risk, Governance, Decision, or Execution.

### INV-08 — Deterministic reproducibility

Given identical historical data, historical data version, strategy versions, and replay configuration, the replay must produce the same deterministic result.

## 10. Explicit Non-Goals

MS-0.11 does not introduce:

- a new trading strategy;
- new H1, M15, Key-Level, Risk, Governance, Session, or Decision rules;
- new execution lifecycle states;
- a one-position restriction;
- fabricated intrabar price paths;
- optimistic or conservative tie-breaking without evidence;
- a competing journal model;
- a competing performance-analytics model;
- live broker or MT5 execution;
- AI-generated trading decisions.

## 11. Architectural Position

MS-0.11 sits downstream of the existing deterministic ASTER pipeline.

```text
                    HISTORICAL DATA
                          │
                          ▼
              ┌──────────────────────┐
              │ BT-D01 Replay Clock  │
              │ Completed candles   │
              │ Explicit cutoff     │
              └──────────┬───────────┘
                         │
                         ▼
              ┌──────────────────────┐
              │ BT-D02 Orchestrator  │
              └──────────┬───────────┘
                         │
          ┌──────────────┼──────────────┐
          ▼              ▼              ▼
       Strategy         Risk        Governance
          │              │              │
          └──────────────┼──────────────┘
                         ▼
                      Decision
                         │
                         ▼
                  Entry Execution
                         │
                         ▼
                      Position
                         │
                   ┌─────┴─────┐
                   ▼           ▼
                 Stop        Target
                   │           │
                   └─────┬─────┘
                         ▼
                BT-D03 Evidence
                         │
                         ▼
                      Journal
                         │
                         ▼
                  Existing Analytics

Replay state:
    BT-D04 Account
    +
    BT-D05 Pending / Active State
    +
    BT-D06 Result / Validation Evidence

The backtester is therefore a historical replay harness around ASTER, not an alternative implementation of ASTER.
 
## 12. Signature Status

The following decisions are frozen conceptually and require no further design choice for implementation:

- BT-D01 — A
- BT-D02 — A
- BT-D03 — C
- BT-D04 — A
- BT-D05 — A
- BT-D06 — A

### Signature refinement

BT-D04 permits the backtester to represent multiple positions. This is a replay capability, not a new authorization rule. Existing Governance, Risk, and Session components remain the authority over whether another position may actually be opened.

**Canonical status: FROZEN.**

No implementation may introduce a new trading rule, authorization rule, or alternate domain semantics under the MS-0.11 backtest layer.
