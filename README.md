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

**Milestone:** MS-0.2 — System Architecture & Technical Design

**Current submilestone:** MS-0.2A — Component Architecture

The Strategy Specification v0.1.0 has been substantially frozen. Remaining implementation-level items are tracked explicitly rather than invented during coding.

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
├── README.md
├── docs/
│   ├── architecture/
│   │   ├── adr/
│   │   ├── component-architecture.md
│   │   ├── data-contracts.md
│   │   ├── decision-state-machine.md
│   │   └── system-overview.md
│   └── ...
└── ...
```

## Development discipline

The smallest working system is preferred over premature complexity. New modules, indicators, AI models, data sources, execution mechanisms, and risk rules require explicit methodological or engineering justification.
