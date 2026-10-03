# MS-0.23 — Qualification Context Contract

Status: implemented from the frozen semantic contract.

## Purpose

MS-0.23 defines the composition boundary between observation orchestration and the Risk/Governance engines.

```
ObservationRunner
      |
      v
Qualification Context
   |          |
   v          v
RiskRequest  GovernanceRequest
   |          |
   v          v
Risk Engine  Governance Engine
```

## Locked decisions

- D01: Qualification Context is an assembler only.
- D02: Risk-context authority is split across six explicit provider ports.
- D03: Daily trade/loss counts come from authoritative completed-trade execution history.
- D04: Required context is captured at qualification time.
- D05: Missing or invalid required context produces a structured fail-closed result.
- D06: Session eligibility is a required prerequisite. Until an authoritative session-eligibility source exists, the assembler fails closed with `SESSION_ELIGIBILITY_UNAVAILABLE`. It must never infer session hours or substitute a hard-coded boolean.

## Provider authority

| Input | Authority |
|---|---|
| `account_equity` | `AccountStatePort` |
| `spread` | `MarketExecutionContextPort` |
| `slippage` | `ExecutionHistoryPort` |
| `daily_trade_count` | `ExecutionHistoryPort` |
| `daily_loss_count` | `ExecutionHistoryPort` |
| `noise` | `NoisePolicyPort` |
| `volatility_adjustment` | `VolatilityPolicyPort` |
| `value_per_price_unit` | `InstrumentSpecificationPort` |
| `instrument_session_eligible` | Explicit prerequisite; authoritative source not yet defined |

The six provider ports remain unchanged. D06 does not add a seventh provider port.

## Qualification result

`QualificationContextResult` has two outcomes:

- `AVAILABLE`: both downstream requests are complete.
- `QUALIFICATION_CONTEXT_UNAVAILABLE`: downstream requests are absent and deterministic reason codes identify the missing/invalid inputs.

Risk and Governance are not invoked with incomplete context.

## Freshness

Context is captured when a candidate is actually qualified. The H1 observation boundary remains authoritative for strategy/market facts; operational context reflects qualification-time state.

## Non-goals

MS-0.23 does not add:

- trading setups;
- entry rules;
- Risk formulas;
- Governance rules;
- execution mechanics;
- broker integration;
- AI/ML authority;
- fallback or synthetic context values.
