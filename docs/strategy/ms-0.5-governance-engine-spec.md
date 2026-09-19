# ASTER — MS-0.5 Governance Engine

## Status
Milestone: MS-0.5
Component: Governance Engine
Status: Deterministic implementation baseline

## Objective
MS-0.5 applies the hard operational controls that determine whether an already risk-qualified trade candidate is permitted to proceed.
Governance does not detect setups, calculate risk, select targets, or modify strategy rules.

## Locked Governance Rules
- G-01: Maximum 2 trades per day
- G-02: Stop trading after 2 losses
- G-03: Trading is restricted to the defined handbook session
- G-04: EUR/USD is governed
- G-05: GBP/USD is governed
- G-06: Risk and Governance remain separate
- G-07: Governance rejection is distinct from Risk rejection
- G-08: Execution requires governance authorization

## Governance Request
The Governance Engine receives a DecisionCandidate, instrument_session_eligible, daily_trade_count, and daily_loss_count.
The session input is a boolean produced by the session/time policy boundary.
MS-0.5 does not invent or redefine the handbook's exact session times. The session-time calculation remains an upstream policy/input concern until the handbook's exact window is formally encoded.

## Instrument Scope
Only EURUSD and GBPUSD are governed in this milestone. Other instruments are deterministically blocked.

## Daily Trade Limit
Eligible only when daily_trade_count < 2. Thus 0 and 1 are eligible; 2 or more is blocked.
The Governance Engine does not count trades itself. It evaluates the supplied daily count.

## Daily Loss Limit
Eligible only when daily_loss_count < 2. Thus 0 and 1 are eligible; 2 or more is blocked.
The Governance Engine does not determine whether a historical trade was a loss. It evaluates the supplied loss count.

## Session Control
Eligible only when instrument_session_eligible is true.
The Governance Engine does not calculate the session window itself.

## Authorization
Governance returns GOVERNANCE_AUTHORIZED when every hard control passes, and GOVERNANCE_BLOCKED when one or more controls fail.
All failed controls are retained as deterministic reason codes.

## Reason Codes
- INSTRUMENT_NOT_GOVERNED
- OUTSIDE_GOVERNED_SESSION
- MAX_DAILY_TRADES_REACHED
- MAX_DAILY_LOSSES_REACHED
- GOVERNANCE_CONTROLS_PASSED

Multiple failures return all applicable rejection reasons in deterministic order.

## Architecture Boundary
DecisionCandidate → GovernanceRequest → GovernanceEngine → GovernanceResult → Decision / Execution Authorization

Governance does not alter the candidate, RiskResult, risk percentage, stop loss, target, strategy qualification, or broker execution, and does not use AI/ML.

## Acceptance Criteria
1. EURUSD candidate within session and limits → authorized.
2. GBPUSD candidate within session and limits → authorized.
3. Unsupported instrument → blocked.
4. Outside session → blocked.
5. Two existing trades → blocked.
6. Two existing losses → blocked.
7. Multiple failed controls → all applicable reason codes retained.
8. Governance status remains distinct from RISK_REJECTED.
9. Exact handbook session timing is not invented inside MS-0.5.
10. Governance remains deterministic and auditable.