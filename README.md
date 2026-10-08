# AI-Assisted, Governed Forex Trading System

A serious, auditable Forex trading decision-support and eventual controlled-execution system built from a documented price-action methodology.

> **The trading system governs the AI. The AI does not own the trading system.**

## Current development status

**Current milestone:** **MS-0.28 — Live Execution Contract**

**Status:** **Canonical specification frozen; implementation and runtime validation in progress**

The canonical MS-0.27 specification was merged into main at:

108597bc9fb3a3e490ddd145e7ac1c0824f92ce0

MS-0.27 defines the platform-neutral production/deployment boundary across:

- Decision-support
- Paper trading
- MT5 demo
- Controlled live

The implementation adds:

- canonical runtime lifecycle: STARTING → INITIALIZING → RUNNING ↔ DEGRADED/RECOVERING → SHUTTING_DOWN → STOPPED;
- explicit dependency health and readiness;
- fail-closed strategy-decision and execution capability gates;
- runtime-scoped execution authorization;
- deterministic recovery semantics for AUTHORIZED, SUBMITTED, FILLED, and FAILED execution state;
- duplicate-execution prevention;
- immutable append-only authoritative-state boundary;
- application, strategy, configuration, and runtime identity;
- platform-neutral persistence and deployment ports.

**Runtime validation:** 284 tests passed in CI on PR #33.

### MS-0.27 explicit non-decisions

MS-0.27 does **not** mandate:

- Docker
- Kubernetes
- a cloud provider
- a cloud secret-management product
- a specific persistence technology
- a specific backup technology
- a monitoring vendor or monitoring stack
- a distributed coordination system
- a broker/MT5 implementation
- a specific deployment platform

These remain implementation or later infrastructure decisions.

## Current control flow

Live Market Data → Validation + Normalization → Strategy qualification → Risk + Governance → Decision → Execution → Position / Exit → Journal → Performance Analytics

Session Policy is a temporal eligibility provider to Governance rather than a downstream execution stage.

Deployment and runtime control sit around this application flow. Deployment capability does not equal execution authorization.

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
11. Production deployment remains platform-neutral until an infrastructure decision is explicitly frozen.

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
- docs/strategy/ms-0.27-production-deployment.md
- docs/strategy/ms-0.28-live-execution-contract.md

## Development discipline

The smallest working system is preferred over premature complexity. New modules, indicators, AI models, data sources, execution mechanisms, infrastructure technologies, and risk rules require explicit methodological or engineering justification.

Contracts are frozen before implementation. Further changes proceed through explicit, versioned decisions and controlled implementation batches.