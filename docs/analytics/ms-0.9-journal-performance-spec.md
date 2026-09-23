# MS-0.9 — Journal / Performance Analytics

## Contract correction

The original implementation used generic names such as `entry_price`, `exit_price`, `opened_at`, `closed_at`, and `quantity`. Those names were too ambiguous for ASTER because the system deliberately separates strategy signal values from actual execution values.

The canonical journal therefore uses execution-aware fields:

- `journal_id` — unique journal-record identity.
- `decision_id` — originating Decision identity.
- `entry_execution_id` — actual entry execution identity.
- `exit_execution_id` — actual exit execution identity.
- `strategy_version` — strategy version attached to the originating decision.
- `symbol` — traded instrument.
- `direction` — direction of the completed trade.
- `executed_quantity` — actual filled quantity; for ASTER's EURUSD/GBPUSD scope this is expressed in base-currency units.
- `entry_execution_price` — actual entry fill price.
- `exit_execution_price` — actual exit fill price.
- `entry_execution_timestamp` — actual entry execution/fill timestamp.
- `exit_execution_timestamp` — actual exit execution/fill timestamp.
- `realized_pnl` — canonical net realized P&L supplied by the journal producer.

`entry_execution_price` must not be populated from `DecisionCandidate.signal_entry_price`, and `exit_execution_price` must not be populated from a target price. Likewise, execution timestamps must come from execution events, not signal timestamps.

## Upstream boundary

MS-0.7 currently defines the entry-side paper execution (`PaperOrder` / `PaperFill`) but does not define an exit-execution contract. Therefore MS-0.9 defines the completed-trade journal schema only; it does not invent or implement an exit path.

A `TradeJournalEntry` is complete only when actual entry and exit execution evidence is supplied by the producer. The journal does not infer missing exit data or realized P&L.

## Performance Metrics

MS-0.9 retains the existing deterministic descriptive metrics: total trades, wins, losses, breakevens, win rate, gross profit, gross loss, net P&L, average trade P&L, profit factor, maximum drawdown, maximum consecutive losses, and expectancy.

Expectancy is defined as average realized P&L per completed trade for this journal's outcome measure. No annualization, Sharpe ratio, forecast, or statistical-significance claim is introduced.

## Ordering

Entries are ordered by `exit_execution_timestamp` ascending, then `journal_id` ascending.

## Authority

Journal and analytics remain observational. They cannot authorize, block, modify, or reinterpret Strategy, Risk, Governance, Decision, Execution, or Session Policy state.

## Explicit non-goals

- No strategy changes.
- No risk or governance changes.
- No Decision changes.
- No execution-state changes.
- No exit-execution implementation in MS-0.9.
- No broker/MT5 integration.
- No reconstruction of P&L from prices.
- No AI/ML prediction.