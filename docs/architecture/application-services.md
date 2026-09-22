# Application and Service Interfaces

## 1. Purpose

MS-0.2D defines the application-layer dependency boundaries for the system. The objective is to make the direction of control explicit before implementing deterministic trading behavior.

The interfaces in `src/trading_system/application/ports.py` are Python `Protocol` contracts. They describe capabilities required by the application layer without coupling it to MT5, a database, a particular data provider, or a concrete strategy implementation.

This milestone does **not** implement any trading rule.

## 2. Port categories

### Data-facing ports

`MarketDataPort` is the application boundary for obtaining **canonical** market candles. External providers and MT5 implementations belong behind this boundary.

The required data flow is:

```text
External/provider raw records
        ↓
Provider/broker adapter
        ↓
Validation
        ↓
Normalization
        ↓
Canonical MarketCandle
        ↓
Application / strategy
```

`MarketDataPort` must not expose provider-specific records. Validation and normalization remain data-layer responsibilities. Their concrete contracts will be introduced when their canonical result semantics are specified; MS-0.2D does not invent additional domain result types for them.

A strategy engine must never consume raw or merely provider-shaped market data.

### Strategy ports

The strategy layer is split into the methodology-specific engines already established by the architecture:

- `H1MarketStructurePort` — H1 regime and structural state evaluation.
- `KeyLevelEnginePort` — approved key-level detection and level state.
- `ConfirmationEnginePort` — CP-1 and CP-2 sequence evaluation.
- `SetupClassifierPort` — conversion of qualifying confirmations into decision candidates.

These ports accept canonical domain models and return canonical domain models. They do not place orders or authorize risk.

`H1MarketStructurePort` requires an explicit `evaluation_cutoff`. The result represents structure **as of that cutoff**, using only completed candles whose close is at or before the boundary. The implementation must reject or otherwise prevent future candles from influencing the result. This boundary exists to preserve H1 close semantics and prevent look-ahead bias during live evaluation, replay, and backtesting.

### Control ports

- `RiskEnginePort` — independent risk assessment.
- `GovernanceEnginePort` — independent governance authorization.

### Session Policy

MS-0.8 introduces the Session Policy Engine as a deterministic temporal eligibility provider to Governance. It evaluates a timezone-aware UTC timestamp and returns the canonical session identity together with `is_trading_permitted`.

The Session Policy Engine owns only session identity and session eligibility. It does not authorize execution, modify strategy qualification, calculate risk, apply holidays or DST adjustments, or contain AI/ML logic.

Governance consumes the session eligibility result as one of its hard operational inputs. Therefore the architectural relationship is:

```text
                 Session Policy
                       │
                       ▼
Strategy → Risk → Governance → Decision → Execution
```

Session Policy is a provider to Governance, not a downstream stage after Execution.

The final typed decision outcome is deliberately deferred. No temporary `str`-based decision contract is exposed by the application port set. The future decision interface will be introduced only when its canonical domain semantics are formally specified.

### Execution port

`ExecutionPort` is the only application boundary through which an authorized decision may reach an external execution adapter.

The interface receives the candidate together with the Risk and Governance results so the concrete execution boundary can verify that both control results are present and authorized before submission. A rejected or blocked control result must never be submitted to a broker.

The port does not own strategy rules and must not reinterpret or silently modify the candidate's immutable signal timestamp or signal entry price. Broker submission and broker fill remain separate execution events.

### Journal and analytics ports

`TradeJournalPort` records and retrieves immutable completed-trade outcomes. It is observational: it does not authorize trades, create exits, or modify execution state.

The MS-0.9 performance analytics service consumes completed journal entries and produces descriptive aggregate metrics. It does not infer missing outcomes, mutate journal entries, or feed decisions back into the trading-control path.

### Audit port

`AuditPort` records material events. Audit is a cross-cutting boundary and does not own strategy, risk, governance, execution, journal, or analytics authority.

## 3. Dependency direction

The intended dependency direction is:

```text
External Systems
      ↓
Adapters
      ↓
Validation / Normalization
      ↓
Canonical Domain Models
      ↓
Strategy Ports / Implementations
      ↓
Setup Classification
      ↓
Risk + Governance
      ↓
Decision (when formally specified)
      ↓
Execution Port
      ↓
Broker / MT5
```

The important rule is that dependencies point **toward abstractions and domain contracts**, not toward concrete external systems.

## 4. Authority boundaries

| Boundary | Owns | Must not own |
|---|---|---|
| Market data | obtaining canonical candles through the data pipeline | trading methodology |
| Data validation/normalization | data integrity and canonical representation | strategy qualification |
| Market structure | H1 regime classification | order execution, risk authorization |
| Key levels | approved level detection/state | broker execution |
| Confirmation | CP-1/CP-2 qualification | risk authorization |
| Setup classifier | candidate construction | final permission to trade |
| Risk | trade risk and geometry | methodology qualification |
| Governance | hard operational permission, including session eligibility | strategy interpretation, session-time calculation |
| Session Policy | UTC session identity and trading eligibility | strategy qualification, risk calculation, final execution authorization |
| Decision | final system outcome once formally specified | broker-specific mechanics |
| Execution | authorized order submission | changing strategy/risk/governance results |
| Audit | evidence recording | changing authoritative state |
| Explanation | human-readable interpretation of recorded evidence | changing decisions |
| Journal | immutable completed-trade outcome records | authorization, exit inference, state mutation |
| Analytics | deterministic descriptive performance analysis | live decision mutation, strategy/risk/governance changes |

## 5. Dependency rules

1. Concrete adapters implement ports; strategy code does not depend directly on provider or broker SDKs.
2. Strategy engines consume domain contracts rather than reaching into other strategy implementations' private state.
3. Risk does not call strategy engines to decide whether its own controls pass.
4. Governance does not modify strategy qualification or risk calculations.
5. Decision logic, when implemented, consumes strategy, risk, and governance outcomes; it does not replace them.
6. Execution is downstream of **authorized Risk and Governance results** and must reject anything else at the execution boundary.
7. Execution must not reinterpret or silently modify the signal's immutable entry price or timestamp.
8. Audit receives evidence from boundaries but cannot authorize, block, or alter a decision.
9. Explanation, journal, and analytics are downstream/observational consumers and cannot mutate authoritative decision state.
10. Session Policy determines temporal eligibility only; Governance remains authoritative for operational permission.
11. AI/ML components, when introduced, must sit behind explicitly bounded interfaces and cannot bypass deterministic strategy, risk, governance, or execution controls.
12. Shared domain models remain in `domain`; application ports must not introduce duplicate representations of the same concept.
13. No interface may silently encode an unresolved methodology decision.
14. No strategy engine may consume raw external-provider data.
15. H1 structure evaluation must be bounded by an explicit evaluation cutoff and must not use candles after that boundary.
16. Session Policy must use the frozen UTC session contract and must not invent holiday, DST, weekend, or Asian-trading exceptions.

## 6. Call-flow boundary

The expected application call flow is:

```text
MarketDataPort
    ↓
validated/normalized canonical market data
    ↓
H1MarketStructurePort(candles, evaluation_cutoff)
    ↓
KeyLevelEnginePort
    ↓
ConfirmationEnginePort
    ↓
SetupClassifierPort
    ↓
DecisionCandidate
    ├──────────────→ RiskEnginePort
    └──────────────→ GovernanceEnginePort
                         ▲
                         │
                 SessionPolicyEngine
                         │
                    UTC timestamp
                         ↓
             Decision layer (deferred contract)
                         ↓
                  authorized outcome
                         ↓
                   ExecutionPort
```

Audit recording is attached to each material boundary rather than inserted as a source of business authority.

## 7. Explicitly deferred interfaces

The following are intentionally not fully specified in MS-0.2D because the corresponding canonical contracts or semantics are not yet frozen:

- feature-engineering result interface;
- concrete data-validation result object;
- concrete normalization result beyond canonical candles;
- final typed decision outcome and decision port;
- explanation request/result contract;
- future backtest/replay service contract;
- concrete broker/MT5 adapter contract;
- persistence/repository interfaces.

Deferral is deliberate. The project should not manufacture abstractions before their semantics are needed.

## 8. Testing boundary

MS-0.2D tests verify that the ports are importable and structurally usable by compatible implementations, and that the H1 boundary requires an explicit evaluation cutoff. Behavioral strategy tests belong to later milestones when the corresponding engines are implemented.

Execution implementations must additionally enforce authorized Risk and Governance results before any broker submission. Signal/execution separation is a domain invariant and should be protected by later architecture/integration tests.

MS-0.9 establishes the journal and descriptive performance analytics contracts without connecting analytics back into the live authorization path.

## 9. Milestone exit condition

MS-0.2D is complete when:

- application ports are defined;
- dependency direction is documented;
- canonical-data boundaries are explicit;
- H1 evaluation has an explicit no-lookahead boundary;
- authority boundaries are explicit;
- execution is separated from strategy, risk, and governance;
- deferred contracts are recorded rather than invented;
- no trading behavior is introduced by the interface layer.
