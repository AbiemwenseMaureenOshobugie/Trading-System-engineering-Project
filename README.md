# AI-Assisted, Governed Forex Trading System

A serious, auditable Forex trading decision-support and eventual controlled-execution system built from a documented price-action methodology.

> **The trading system governs the AI. The AI does not own the trading system.**

## Project purpose

This project turns the frozen Strategy Specification v0.1.0 into a deterministic, testable, auditable engineering system. The initial scope is EUR/USD and GBP/USD using an H1-to-M15 price-action workflow.

The system is not designed as a generic buy/sell predictor. Deterministic strategy rules, risk controls, governance controls, and execution authorization remain authoritative. AI/ML components may assist with interpretation and explanation, but cannot override hard constraints.

## Strategy Specification v0.1.0

- **Primary timeframe:** H1 for market structure, context, key levels, and directional bias.
- **Confirmation timeframe:** M15 for confirmation and entry refinement.
- **Confirmation processes:** CP-1 breakout/retest continuation and CP-2 key-level rejection, including its sweep variant.
- **H1 regimes:** UPTREND, DOWNTREND, RANGE, TRANSITION, UNCLEAR.
- **Minimum risk/reward:** 1:2.
- **Risk guideline:** approximately 1–2% per trade.
- **Daily trade limit:** maximum 2 trades.
- **Loss control:** stop after 2 losses in a day.
- **Session:** the defined session from the trading handbook.
- **Initial operating path:** Observer → Decision Support → Paper Trading → Demo → Controlled Live.

## Engineering principles

1. The personal Forex handbook is the source of truth for trading methodology.
2. Frozen decisions are not silently changed during implementation.
3. Unresolved methodology questions remain explicitly marked as pending.
4. Deterministic rules govern strategy qualification.
5. Risk and governance are independent control layers.
6. AI cannot bypass risk, governance, or execution authorization.
7. Strategy signal prices/timestamps remain distinct from broker execution prices/timestamps.
8. Every material decision must be explainable and auditable.
9. Backtesting must prevent look-ahead bias, leakage, and accidental use of future information.
10. Project changes are committed in coherent batches rather than unnecessary micro-commits.

## Current development status

**Current milestone:** **MS-0.11 — Backtest / Historical Replay**

**Status:** Complete / Frozen

**Current `main` HEAD:** `bf8b9d6a037834cd215ccd1a77091fc2ffe1a3d9`

**Validation:** **142 tests passing** on the current MS-0.11 baseline.

**Completed milestones:** MS-0.1A through MS-0.11

### Recent completion history

| Milestone | Area | Status |
|---|---|---|
| MS-0.9 | Journal / Performance Analytics | Complete |
| MS-0.10 | Exit Execution Contract | Complete |
| MS-0.11 | Backtest / Historical Replay | Complete / Frozen |

### MS-0.10 — Exit Execution Contract

MS-0.10 defined deterministic exit instructions, exit authorization, exit lifecycle, paper-exit evidence, and journal evidence semantics. It kept Risk responsible for stop/target geometry, Position/Exit Management responsible for exit instructions, Execution responsible for submission/fill evidence, Journal responsible for completed-trade records, and Analytics responsible for descriptive analysis.

MS-0.10 did not introduce a new strategy, risk formula, governance rule, broker state, partial-fill model, retry model, or reconciliation model.

### MS-0.11 — Backtest / Historical Replay

MS-0.11 adds deterministic historical replay and backtesting around the existing ASTER pipeline.

The backtest framework is a **replay harness, not a second trading engine**. It does not reimplement H1 structure, Key-Level detection, M15 confirmation, setup classification, Risk, Governance, Session Policy, Decision precedence, execution-state rules, or position/exit rules.

Its responsibilities are limited to:

- chronological historical replay;
- explicit historical-information cutoffs;
- orchestration of existing deterministic components;
- replay account and position state;
- preservation of pending strategy and active exit state;
- evidence-based historical execution resolution;
- deterministic backtest results and validation evidence.

The fundamental replay boundary is the completed historical candle. For replay cutoff **T**, every strategy input timestamp must be **≤ T**. When historical OHLC data cannot establish the ordering of competing intrabar events, the backtest preserves the ambiguity rather than fabricating an outcome.

Architecturally:

```text
Historical Data
      ↓
Replay Cutoff
      ↓
Existing ASTER Strategy
      ↓
Existing Risk + Governance + Session
      ↓
Existing Decision
      ↓
Existing Execution
      ↓
Replay Account / Positions
      ↓
Existing Journal
      ↓
Existing Performance Analytics
```

The backtest layer therefore remains downstream orchestration and historical state management. It does not become an alternate source of trading authority.

## Current control flow

The deterministic control path is:

```text
Strategy qualification
        ↓
Risk + Governance
        ↓
Decision
        ↓
Execution
        ↓
Position / Exit
        ↓
Journal
        ↓
Performance Analytics
```

Session Policy is a temporal eligibility provider to Governance rather than a downstream execution stage:

```text
                 Session Policy
                       │
                       ▼
Strategy → Risk → Governance → Decision → Execution
                                           │
                                           ▼
                                     Position / Exit
                                           │
                                           ▼
                                        Journal
                                           │
                                           ▼
                                      Analytics
```

Governance remains authoritative for operational permission. Session Policy supplies the session-eligibility input; it does not independently authorize execution.

Historical replay sits around this existing deterministic path as an orchestration layer; it does not replace any of these authorities.

## Planned evolution

Future milestones require explicit authorization before implementation. The milestone list is a planning map, **not automatic authorization**.

Potential future areas include:

1. **MS-0.12 — MT5 broker/demo integration**
2. **MS-0.13 — Controlled live execution**
3. **MS-0.14 — Bounded AI/ML assistance**
4. **MS-0.15 — Production deployment**
5. **MS-0.16 — Independent Prior High/Low Resolution**

**MT5 integration is not currently authorized.** No external broker/MT5 execution adapter should be implemented merely because it appears in the planned evolution.

The next milestone will be selected explicitly after documentation synchronization and validation.

## Documentation

Project documentation is treated as a first-class engineering artifact. Architecture, requirements, decisions, implementation changes, validation results, experiments, and operational history are documented as the project evolves.

Key milestone specifications include:

- `docs/strategy/ms-0.1a-market-structure-spec.md`
- `docs/strategy/ms-0.2-key-level-spec.md`
- `docs/strategy/ms-0.3-confirmation-spec.md`
- `docs/strategy/ms-0.4-risk-and-trade-qualification.md`
- `docs/strategy/ms-0.5-governance-engine-spec.md`
- `docs/strategy/ms-0.6-decision-engine-spec.md`
- `docs/strategy/ms-0.7-execution-contract.md`
- `docs/strategy/ms-0.8-session-policy-spec.md`
- `docs/analytics/ms-0.9-journal-performance-spec.md`
- `docs/execution/ms-0.10-exit-execution-contract.md`
- `docs/strategy/ms-0.11-backtest-historical-replay-contract.md`

## Repository structure

```text
.
├── README.md
├── pyproject.toml
├── src/
│   └── trading_system/
│       ├── application/
│       │   ├── __init__.py
│       │   └── ports.py
│       ├── domain/
│       │   ├── enums.py
│       │   └── models.py
│       ├── data/
│       ├── features/
│       ├── strategy/
│       │   ├── market_structure/
│       │   ├── key_levels/
│       │   └── confirmation/
│       ├── risk/
│       ├── governance/
│       ├── decision/
│       ├── execution/
│       ├── session/
│       ├── journal/
│       ├── audit/
│       ├── analytics/
│       ├── explanation/
│       └── adapters/
├── tests/
│   ├── unit/
│   └── integration/
└── docs/
    ├── analytics/
    ├── architecture/
    ├── execution/
    └── strategy/
```

## Development discipline

The smallest working system is preferred over premature complexity. New modules, indicators, AI models, data sources, execution mechanisms, and risk rules require explicit methodological or engineering justification.

MS-0.11 completes the deterministic historical replay/backtesting boundary without changing the underlying trading methodology or introducing a second trading engine. Further milestones will extend the system only through explicit, versioned decisions and controlled implementation batches.
