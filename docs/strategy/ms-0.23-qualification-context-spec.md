# MS-0.23 — Qualification Context Contract

Status: implemented from the frozen semantic contract.

## Purpose

MS-0.23 defines the composition boundary between observation orchestration and the Risk/Governance engines.

Qualification Context is an assembler. It does not own the policy that determines whether trading is permitted.

```
SessionPolicyEngine (MS-0.8)
          |
          | SessionPolicyResult.is_trading_permitted
          v
Qualification Context
      |             |
      |             |
      v             v
RiskRequest   GovernanceRequest
      |             |
      v             v
Risk Engine   Governance Engine (MS-0.5)
```

The MS-0.8 Session Policy result is authoritative for session eligibility. MS-0.23 only supplies that authoritative result into the Governance qualification context; it does not calculate, reinterpret, or replace it.

## Locked decisions

- D01: Qualification Context is an assembler only.
- D02: Risk-context authority is split across six explicit provider ports.
- D03: Daily trade/loss counts come from authoritative completed-trade execution history.
- D04: Required context is captured at qualification time.
- D05: Missing or invalid required context produces a structured fail-closed result.
- D06: If required qualification context cannot be assembled because an authoritative provider result is unavailable or invalid, qualification fails closed with `QUALIFICATION_CONTEXT_UNAVAILABLE`; downstream Risk/Governance evaluation is not invoked. D06 does not transfer ownership of any policy to MS-0.23.

## Provider authority

### Risk-context authorities

| Input | Authority |
|---|---|
| `account_equity` | `AccountStatePort` |
| `spread` | `MarketExecutionContextPort` |
| `slippage` | `ExecutionHistoryPort` |
| `noise` | `NoisePolicyPort` |
| `volatility_adjustment` | `VolatilityPolicyPort` |
| `value_per_price_unit` | `InstrumentSpecificationPort` |

These authorities supply the context required to construct `RiskRequest`. They do not prescribe broker APIs or concrete implementations.

### Governance/session authority

Session eligibility follows a separate authoritative policy path:

```
SessionPolicyEngine (MS-0.8)
        |
        | produces SessionPolicyResult
        v
Qualification Context
        |
        | extracts is_trading_permitted
        v
instrument_session_eligible
        |
        v
GovernanceRequest
        |
        v
GovernanceEngine (MS-0.5)
```

MS-0.8 owns:

- session identity;
- session boundaries;
- `is_trading_permitted`;
- the authoritative session-policy result.

MS-0.23 owns:

- receiving the authoritative Session Policy result;
- extracting `is_trading_permitted` into `instrument_session_eligible`;
- constructing `GovernanceRequest`.

MS-0.5 owns:

- applying session eligibility as an existing governance condition;
- daily trade-count controls;
- daily loss-count controls;
- final governance authorization.

MS-0.23 must not calculate session eligibility or invent a fallback value when the authoritative Session Policy result is unavailable.

## Qualification result

`QualificationContextResult` has two outcomes:

- `AVAILABLE`: all required downstream qualification inputs are complete and valid, including the authoritative session-eligibility result required for `GovernanceRequest`.
- `QUALIFICATION_CONTEXT_UNAVAILABLE`: one or more required inputs are absent or invalid, with deterministic reason codes identifying the failed context requirement.

Risk and Governance are not invoked with incomplete context.

In particular, if the MS-0.8 Session Policy result cannot be obtained or fails its required composition contract:

```
SessionPolicyEngine unavailable/invalid
        |
        v
required qualification context unavailable
        |
        v
QUALIFICATION_CONTEXT_UNAVAILABLE
        |
        v
Governance is NOT invoked
```

MS-0.23 must not pass `instrument_session_eligible=None` to Governance and must not convert the missing result into `False` as a fallback. Fail-closed occurs at qualification-context assembly.

## Freshness

Context is captured when a candidate is actually qualified. The H1 observation boundary remains authoritative for strategy/market facts; operational context reflects qualification-time state. The authoritative MS-0.8 session-policy result is likewise supplied as qualification context rather than recalculated by MS-0.23.

## Non-goals

MS-0.23 does not add:

- trading setups;
- entry rules;
- Risk formulas;
- Governance rules;
- session-policy rules or session boundaries;
- execution mechanics;
- broker integration;
- AI/ML authority;
- fallback or synthetic context values.
