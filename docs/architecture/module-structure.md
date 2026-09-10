# Module and Package Structure

## Purpose

MS-0.2B establishes the initial Python package boundary for the trading system. These modules are structural boundaries only; trading rules and domain behavior are introduced in later milestones.

## Package layout

```text
.
├── pyproject.toml
├── src/
│   └── trading_system/
│       ├── domain/
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
│       ├── audit/
│       ├── analytics/
│       ├── explanation/
│       └── adapters/
└── tests/
    ├── unit/
    └── integration/
```

## Responsibilities

- `domain`: authoritative domain objects and contracts shared across boundaries.
- `data`: market-data validation, normalization, and data-facing application services.
- `features`: deterministic derived observations used by strategy logic.
- `strategy`: methodology-specific deterministic qualification.
  - `market_structure`: H1 structure and regime classification.
  - `key_levels`: approved key-level detection and state.
  - `confirmation`: M15 CP-1 and CP-2 confirmation sequences.
- `risk`: trade geometry and risk authorization.
- `governance`: hard operational permissions and constraints.
- `decision`: orchestration of qualification, risk, and governance outcomes.
- `execution`: controlled broker/MT5 boundary; no direct bypass of authorization.
- `audit`: immutable decision and execution evidence.
- `analytics`: backtesting, replay, and performance analysis.
- `explanation`: human-readable explanations derived from recorded evidence.
- `adapters`: external-system implementations such as market-data and broker adapters.

## Dependency rules

1. External adapters do not contain trading methodology.
2. Strategy modules do not place broker orders.
3. Risk and governance remain independent of strategy implementation details.
4. Execution accepts only authorized decisions.
5. Explanation does not mutate authoritative decision state.
6. Analytics may replay the system but does not alter live state.
7. Shared domain contracts belong in `domain`; arbitrary cross-package utility coupling should be avoided.
8. Future AI/ML components must remain subordinate to deterministic strategy, risk, and governance controls.

## Scope of this milestone

MS-0.2B intentionally creates no indicators, trading rules, broker integration, database layer, ML model, or live execution logic. The objective is a clean importable skeleton that gives subsequent implementation work a stable boundary.

## Versioning

The package begins at version `0.1.0`, aligned with the current Strategy Specification baseline. Strategy specification versions and Python package versions are related but remain separate concepts.
