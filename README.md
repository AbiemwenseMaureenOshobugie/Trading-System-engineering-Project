# AI-Assisted, Governed Forex Trading System

A serious, auditable Forex trading decision-support and eventual controlled-execution system built from a documented price-action methodology.

> **The trading system governs the AI. The AI does not own the trading system.**

## Current development status

**Current milestone:** **MS-0.13 — Live Market Data Adapter**

**Status:** **Contract frozen — implementation next**

**Current main HEAD before this documentation commit:** 994a20ea

**Completed milestones:** MS-0.1A through MS-0.12

### MS-0.13 — Live Market Data Adapter

MS-0.13 freezes the first external live market-data boundary.

The locked contract uses **Twelve Data** as the first provider and keeps provider-specific identifiers behind the adapter boundary.

The adapter:
- publishes only completed canonical MarketCandle records;
- owns the mapping from ASTER symbols EURUSD / GBPUSD to provider symbols;
- fails closed on invalid, unavailable, stale, incomplete, duplicated, or otherwise unreliable market data;
- uses boundary-driven REST polling;
- preserves source identity and auditable retrieval/provenance metadata;
- accepts an explicit operational warm-up window without inventing a strategy lookback.

WebSocket streaming, TradingView integration, MT5 market-data integration, live orders, AI/ML interpretation, strategy changes, new Risk/Governance/Session rules, and portfolio logic are outside MS-0.13.

The canonical contract is docs/strategy/ms-0.13-live-market-data-adapter.md.

## Current control flow

Live Market Data → Validation + Normalization → Strategy qualification → Risk + Governance → Decision → Execution → Position / Exit → Journal → Performance Analytics

Session Policy is a temporal eligibility provider to Governance rather than a downstream execution stage.

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

## Documentation

Key milestone specifications include:
- docs/strategy/ms-0.1a-market-structure-spec.md
- docs/strategy/ms-0.2-key-level-spec.md
- docs/strategy/ms-0.3-confirmation-spec.md
- docs/strategy/ms-0.4-risk-and-trade-qualification.md
- docs/strategy/ms-0.5-governance-engine-spec.md
- docs/strategy/ms-0.6-decision-engine-spec.md
- docs/strategy/ms-0.7-execution-contract.md
- docs/strategy/ms-0.8-session-policy-spec.md
- docs/analytics/ms-0.9-journal-performance-spec.md
- docs/execution/ms-0.10-exit-execution-contract.md
- docs/strategy/ms-0.11-backtest-historical-replay-contract.md
- docs/strategy/ms-0.12-mt5-demo-adapter.md
- docs/strategy/ms-0.13-live-market-data-adapter.md

## Development discipline

The smallest working system is preferred over premature complexity. New modules, indicators, AI models, data sources, execution mechanisms, and risk rules require explicit methodological or engineering justification.

MS-0.13 is contractually frozen before implementation. Further changes will proceed through explicit, versioned decisions and controlled implementation batches.