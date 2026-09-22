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

**Milestone:** MS-0.8 â€” Session / Time Policy Engine

**Status:** Complete

**Current HEAD:** 8c705e738f48eac93688c94862be42c7cf5d5aa1

**Test suite:** 88 passed

**Completed milestones:** MS-0.1A through MS-0.8

MS-0.8 establishes the deterministic session/time policy boundary. The Session Policy Engine classifies a UTC timestamp into the canonical session identity and produces a trading-eligibility result. Governance consumes that eligibility as an input to its hard operational permission checks. Session Policy does not modify strategy, risk, decision, or execution rules and does not introduce holiday or DST logic. The execution boundary established by MS-0.7 remains downstream of authorized Decision, Risk, and Governance results.

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
```

Session Policy is a temporal eligibility provider to Governance rather than a downstream execution stage:

```text
                 Session Policy
                       │
                       ▼
Strategy → Risk → Governance → Decision → Execution
```

Governance remains authoritative for operational permission. Session Policy supplies the session-eligibility input; it does not independently authorize execution.

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

MS-0.8 completes the current deterministic control pipeline by adding session eligibility as an explicit input to Governance. Further milestones will extend the system only through explicit, versioned decisions and controlled implementation batches.

