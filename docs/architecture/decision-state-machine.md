# Decision State Machine

## 1. Purpose

The decision state machine prevents the strategy from being implemented as a collection of disconnected boolean conditions. It represents the lifecycle of a setup from observation through invalidation, qualification, authorization, and execution.

## 2. High-level lifecycle

```text
OBSERVING
   ↓
CONTEXT_VALID
   ↓
SETUP_DETECTED
   ↓
CONFIRMING
   ├── invalidated → OBSERVING
   └── confirmed → CANDIDATE
                    ↓
                 RISK_CHECK
                    ├── rejected → BLOCKED
                    └── authorized
                           ↓
                    GOVERNANCE_CHECK
                    ├── blocked → BLOCKED
                    └── authorized
                           ↓
                       VALID
                           ↓
                   SIGNAL_GENERATED
                           ↓
                PAPER / EXECUTION_PENDING
                           ↓
                     EXECUTED
                           ↓
                      CLOSED
```

## 3. Important state semantics

### OBSERVING
No active qualifying setup exists. Market data continues to be evaluated.

### CONTEXT_VALID
Required H1 context and structural conditions are available for the relevant strategy process.

### SETUP_DETECTED
A possible CP-1 or CP-2 process has begun, but confirmation is not complete.

### CONFIRMING
The engine is tracking a defined multi-candle sequence. Each required candle must satisfy the frozen conditions. Failure creates an invalidation event; the engine does not salvage the sequence by changing its interpretation.

### CANDIDATE
The strategy has produced a valid decision candidate with an immutable signal definition.

### RISK_CHECK
The Risk Engine independently evaluates trade geometry and permitted risk.

### GOVERNANCE_CHECK
The Governance Engine independently checks hard constraints such as instrument, session, daily trade count, and loss-stop rules.

### VALID
The candidate has passed strategy, risk, and governance requirements. This does not imply that the broker has filled an order.

### SIGNAL_GENERATED
The strategy signal is recorded at its defined signal timestamp and signal entry price.

### EXECUTION_PENDING
An authorized signal may be submitted to the broker when execution is enabled. Submission and fill are separate events.

### EXECUTED
A broker execution has occurred and is recorded separately from the signal.

### CLOSED
The position has a completed outcome and becomes available for performance analytics.

### BLOCKED
The candidate cannot proceed. The reason must distinguish strategy invalidation, `RISK_REJECTED`, and `GOVERNANCE_BLOCKED` where applicable.

## 4. H1 invalidation priority

Confirmed H1 structural invalidation has priority over an active pre-entry M15 confirmation sequence. For a bullish setup, a completed H1 candle closing below the controlling meaningful HL invalidates the bullish structure. For a bearish setup, a completed H1 candle closing above the controlling meaningful LH invalidates the bearish structure.

An H1 wick alone does not invalidate structure.

If an M15 trigger has already generated a signal before the H1 candle closes, later H1 invalidation is a post-signal/post-entry event rather than a retroactive cancellation.

## 5. Sequence immutability

Once CP-2 C1 closes, the sweep controlling extreme is frozen for a sweep sequence. A later more extreme penetration does not update the existing sequence; it constitutes a new sweep event requiring a fresh qualifying rejection. Similar immutability applies to the governing key level and C1 identity.

## 6. Signal versus execution

The state machine must preserve:

- strategy signal timestamp and signal entry price;
- order submission timestamp and order details;
- broker execution timestamp, execution price, quantity, order ID, and slippage.

A broker fill must never overwrite the historical strategy signal.
