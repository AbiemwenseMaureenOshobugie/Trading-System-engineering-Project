# ADR-0001: Architecture Principles

- **Status:** Accepted
- **Date:** 2026-09-09
- **Decision:** Establish the initial architecture around deterministic strategy rules, independent risk and governance controls, auditable state, and a staged execution boundary.

## Context

The project is intended to become a serious Forex decision-support and eventually controlled-execution system. The trading methodology is documented separately and is the source of truth. The engineering system must preserve that methodology without allowing AI or implementation convenience to silently redefine it.

## Decisions

### 1. Deterministic rules remain authoritative

Market structure, key levels, confirmation sequences, entry rules, and hard constraints are implemented as explicit deterministic logic wherever the methodology provides deterministic requirements.

### 2. AI is subordinate to system governance

AI/ML may assist with interpretation, explanation, research, or later validated enhancements. It cannot override strategy constraints, risk limits, governance blocks, or execution authorization.

### 3. Risk and governance are separate components

Risk evaluates trade-level financial geometry and permitted risk. Governance evaluates hard operational permissions and constraints. Their outcomes remain distinguishable.

### 4. Signal and execution are separate

A strategy signal is a decision produced by the methodology. Broker execution is an external operational event. The two records must never be conflated.

### 5. Auditability is a first-class requirement

Material decisions must be traceable to input data, derived observations, strategy version, rule evaluations, risk results, governance results, and execution/outcome records.

### 6. Staged deployment is mandatory

The system progresses from observation to decision support, paper trading, demo, and only much later controlled live execution. Live trading is not the initial implementation target.

### 7. Avoid premature infrastructure

The initial system should remain a modular Python application with clear boundaries. Microservices, Kubernetes, cloud infrastructure, complex AI agents, and other infrastructure are not introduced until a demonstrated requirement exists.

### 8. Methodological ambiguity is explicit

When the handbook does not specify a rule sufficiently for deterministic implementation, the requirement is recorded as pending. The implementation must not invent a numerical threshold or additional trading concept merely to make the code convenient.

## Consequences

This architecture favors correctness, reproducibility, and governance over rapid feature expansion. Some implementation questions will remain deliberately pending until they can be resolved from the methodology or controlled testing. The resulting system should be easier to backtest, audit, and validate before any real-money execution is considered.
