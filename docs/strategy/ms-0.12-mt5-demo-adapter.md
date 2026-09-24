# MS-0.12 — MT5 Demo Adapter

## Status

Canonical specification for the first MT5 connectivity milestone.

MS-0.12 introduces MT5 only as an external execution adapter. Strategy, Risk,
Governance, Decision, and historical replay semantics remain unchanged.

### MT5-D01 — Adapter boundary

A dedicated MT5 adapter implements the existing `ExecutionPort` and
`ExitExecutionPort`. Core modules do not import the `MetaTrader5` package.

### MT5-D02 — Adapter connection lifecycle

Adapter state is:

`UNINITIALIZED → CONNECTED → READY → DISCONNECTED`

This is independent of ASTER's execution lifecycle:
`AUTHORIZED → SUBMITTED → FILLED | FAILED`.

### MT5-D03 — Demo account only

MS-0.12 may submit only when MT5 account information reports the official
demo trade mode. The guard is machine-readable; server-name strings are not
used as proof of demo status.

### MT5-D04 — Market entry

Entry uses an MT5 market-deal request. ASTER's signal entry price remains
immutable reference evidence. Actual MT5 fill price and quantity are stored
separately as execution truth.

### MT5-D05 — Symbol and quantity translation

ASTER symbols map to broker symbols through configuration. ASTER quantity is
validated against MT5 minimum, maximum, and step constraints. No upward
rounding is permitted.

### MT5-D06 — Failure semantics

Submission or broker rejection produces `FAILED` execution evidence. There
is no automatic retry.

A partial-fill result is unsupported in MS-0.12 and fails closed as an
explicit adapter error requiring future reconciliation semantics. It must not
be represented as a clean full fill or a clean failed trade.

Submission failure may transition directly from authorization to `FAILED`
because no successful broker submission occurred.

### MT5-D07 — Hard safety guard

If the connected account is not demonstrably a demo account, no broker order
may be submitted.

### Broker evidence

Broker order/deal identifiers, actual fill price/quantity, execution
timestamp, return code, broker status, and execution-side slippage are kept
separate from ASTER signal/reference data.

For exits, an MT5 position identifier is required. No symbol-only position
guessing is permitted.

### Non-goals

No live trading, automatic retry, partial-fill reconciliation, recovery
workflow, portfolio controls, or new trading methodology/risk/governance rules.
