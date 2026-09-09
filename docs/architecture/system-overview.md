# System Overview

## 1. Purpose

This document defines the high-level architecture for Strategy Specification v0.1.0. It describes system boundaries and responsibility flow without prematurely fixing implementation details that belong to lower-level design.

## 2. Core principle

**The trading system governs the AI. The AI does not own the trading system.**

The deterministic strategy, risk, governance, and execution-authorization layers are authoritative. AI/ML may assist interpretation, explanation, research, or later validated enhancements, but cannot bypass hard controls.

## 3. End-to-end flow

```text
Market Data
    ↓
Data Validation
    ↓
Normalization
    ↓
Feature Engineering
    ↓
H1 Market Structure
    ↓
Key-Level Detection
    ↓
M15 Confirmation
    ↓
Setup Classification
    ↓
Risk Calculation
    ↓
Governance Check
    ↓
Decision Engine
    ↓
Explanation / Alert / Paper Trade
    ↓
Journal
    ↓
Performance Analytics
```

When execution is eventually enabled, the controlled path becomes:

```text
Decision Candidate
    ↓
Deterministic Strategy Rules
    ↓
Risk Engine
    ↓
Governance Engine
    ↓
Execution Authorization
    ↓
Broker / MT5
```

## 4. System boundaries

### Inside the system

- Market-data ingestion and validation
- Timeframe normalization
- Market-structure reconstruction
- Key-level detection
- CP-1 and CP-2 confirmation logic
- Entry, stop-loss, and target calculations permitted by the specification
- Risk and governance controls
- Decision and state management
- Audit logging and journaling
- Backtesting and performance analytics
- Explanations and alerts
- Eventually, controlled broker execution

### Outside the system

- Broker infrastructure
- MetaTrader 5 terminal and broker account
- External market-data providers
- GitHub and project-development infrastructure
- Human approval and operational oversight

## 5. Operating stages

The system will progress through controlled stages:

1. **Observer** — validate data and detect methodology events without trading.
2. **Decision Support** — produce VALID, WAIT, or BLOCKED outcomes with explanations.
3. **Paper Trading** — simulate signals and execution separately.
4. **Demo** — integrate with MT5 under controlled conditions.
5. **Controlled Live** — only after sufficient validation, governance approval, and operational readiness.

## 6. Architectural constraints

- Strategy rules must be deterministic and testable.
- Risk Engine must be independent of Strategy Engine.
- Governance Engine must be independent of Risk Engine.
- AI cannot change risk limits or bypass governance.
- Signal entry and broker execution must remain separate records.
- Every material decision must be reproducible from recorded inputs, strategy version, and rule outcomes.
- The architecture must support EUR/USD and GBP/USD without duplicating the core strategy implementation.
- No unnecessary microservices or infrastructure are introduced at this stage.
