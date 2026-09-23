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
- **Risk guideline:** approximately 1â€“2% per trade.
- **Daily trade limit:** maximum 2 trades.
- **Loss control:** stop after 2 losses in a day.
- **Session:** the defined session from the trading handbook.
- **Initial operating path:** Observer â†’ Decision Support â†’ Paper Trading â†’ Demo â†’ Controlled Live.

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

**Milestone:** MS-0.9 — Journal / Performance Analytics

**Status:** Complete

**Current main:** PR #8 merged; MS-0.9 is corrected and complete.

**Verification:** 124 tests passing.

**Completed milestones:** MS-0.1A through MS-0.9

MS-0.9 establishes the deterministic journal and descriptive performance-analytics boundary. Completed trade outcomes are represented as immutable journal entries; analytics aggregates supplied realized P&L into deterministic descriptive metrics. The journal and analytics layers do not authorize, mutate, or reinterpret Strategy, Risk, Governance, Decision, Execution, or Session Policy state.

### Current open items

| Item | Status |
|---|---|
| Independent Prior High/Low (K-04 old) | 🟡 Unresolved |
| MT5/Broker integration | ⏸️ Deferred |
| Live execution | ⏸️ Deferred |
| Partial fills | ⏸️ Deferred |
| Cancellations | ⏸️ Deferred |
| Retry/recovery | ⏸️ Deferred |
| Reconciliation | ⏸️ Deferred |
| Exit execution contract | ⏳ New gap; planned for MS-0.10 |

### MS-0.10 dependency

The MS-0.9 journal schema now records actual exit-execution fields, but MS-0.9 deliberately does not invent an exit mechanism. The entry-execution contract exists in MS-0.7; an equivalent exit-execution contract does not yet exist.

**MS-0.10 — Exit Execution Contract** is therefore the next execution-contract milestone. It depends on the MS-0.7 entry-execution boundary and the MS-0.9 journal schema. Until that contract is defined and implemented, the journal remains a schema/analytics boundary rather than an exit-generation mechanism.

## Planned evolution

The system will evolve through controlled stages:

1. Market observation and data validation
2. Deterministic decision support
3. Paper trading
4. MT5 demo integration
5. Controlled live execution, only after sufficient validation and governance approval
6. AI/ML assistance where it demonstrates measurable value without weakening system controls

## Documentation

Project documentation is treated as a first-class engineering artifact. Architecture, requirements, decisions, implementation changes, validation results, experiments, and operational history will be documented as the project evolves.

## Repository structure

```text
.
â”œâ”€â”€ README.md
â”œâ”€â”€ pyproject.toml
â”œâ”€â”€ src/
â”‚   â””â”€â”€ trading_system/
â”‚       â”œâ”€â”€ application/
â”‚       â”‚   â”œâ”€â”€ __init__.py
â”‚       â”‚   â””â”€â”€ ports.py
â”‚       â”œâ”€â”€ domain/
â”‚       â”‚   â”œâ”€â”€ enums.py
â”‚       â”‚   â””â”€â”€ models.py
â”‚       â”œâ”€â”€ data/
â”‚       â”œâ”€â”€ features/
â”‚       â”œâ”€â”€ strategy/
â”‚       â”‚   â”œâ”€â”€ market_structure/
â”‚       â”‚   â”œâ”€â”€ key_levels/
â”‚       â”‚   â””â”€â”€ confirmation/
â”‚       â”œâ”€â”€ risk/
â”‚       â”œâ”€â”€ governance/
â”‚       â”œâ”€â”€ decision/
â”‚       â”œâ”€â”€ execution/
â”‚       â”œâ”€â”€ session/
â”‚       â”œâ”€â”€ journal/
â”‚       â”œâ”€â”€ audit/
â”‚       â”œâ”€â”€ analytics/
â”‚       â”œâ”€â”€ explanation/
â”‚       â””â”€â”€ adapters/
â”œâ”€â”€ tests/
â”‚   â”œâ”€â”€ unit/
â”‚   â”‚   â”œâ”€â”€ test_domain_models.py
â”‚   â”‚   â””â”€â”€ test_application_ports.py
â”‚   â””â”€â”€ integration/
â””â”€â”€ docs/
    â””â”€â”€ architecture/
        â”œâ”€â”€ application-services.md
        â””â”€â”€ ...
```

## Development discipline

The smallest working system is preferred over premature complexity. New modules, indicators, AI models, data sources, execution mechanisms, and risk rules require explicit methodological or engineering justification.

MS-0.9 extends the completed deterministic control pipeline with an observational journal and performance-analytics layer. These components describe completed outcomes without becoming a source of trading authority. Further milestones will extend the system only through explicit, versioned decisions and controlled implementation batches.

