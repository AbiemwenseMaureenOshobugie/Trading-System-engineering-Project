# ASTER — MS-0.6 Decision Engine

## Objective

MS-0.6 is the deterministic aggregation boundary between Strategy/Risk/Governance and downstream execution.

It does not create trading rules. It only interprets the authoritative upstream outcomes.

## Decision States

- NO_SETUP — no strategy candidate exists and strategy is not pending.
- WAIT — the system has an unresolved upstream condition.
- VALID — a candidate exists, Risk is authorized, and Governance is authorized.
- RISK_REJECTED — Risk produced a rejection.
- GOVERNANCE_BLOCKED — Risk authorized the candidate, but Governance blocked it.

## Decision Request

The engine receives:

- optional DecisionCandidate;
- strategy_pending;
- optional RiskResult;
- optional GovernanceResult.

The orchestration layer owns the meaning of strategy_pending; MS-0.6 does not invent a new strategy condition.

## Precedence

1. No candidate + strategy pending → WAIT.
2. No candidate + not pending → NO_SETUP.
3. Candidate + no Risk result → WAIT.
4. Risk rejected → RISK_REJECTED.
5. Risk authorized + no Governance result → WAIT.
6. Governance blocked → GOVERNANCE_BLOCKED.
7. Risk authorized + Governance authorized → VALID.

A Governance result is not evaluated before Risk authorization.

## Architecture Boundary

Strategy → DecisionCandidate → Risk → Governance → Decision → Execution

The Decision Engine aggregates upstream state, produces one final decision status, preserves upstream rejection reason codes, and remains deterministic and auditable.

It does not modify Strategy, calculate Risk, change SL/TP, override Governance, authorize broker execution by itself, or use AI/ML.

## Session Timing

The unresolved MS-0.5 session-timing gap remains outside MS-0.6. The Decision Engine consumes the Governance result and does not define session hours.

## Acceptance Criteria

1. No candidate produces NO_SETUP.
2. Pending strategy produces WAIT.
3. Missing Risk result produces WAIT.
4. Risk rejection produces RISK_REJECTED.
5. Missing Governance result after Risk authorization produces WAIT.
6. Governance rejection produces GOVERNANCE_BLOCKED.
7. Only Risk + Governance authorization produces VALID.
8. Upstream reason codes remain preserved.
9. No strategy/risk/governance rules are duplicated inside Decision Engine.
