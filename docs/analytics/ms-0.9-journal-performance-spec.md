# MS-0.9 — Journal / Performance Analytics

## Objective

Introduce a deterministic trade-journal boundary and descriptive performance analytics without changing strategy, risk, governance, decision, execution, or session-policy rules.

## Scope

MS-0.9 provides:

1. an immutable canonical `TradeJournalEntry` for a completed trade;
2. a journal port for recording and retrieving completed trade entries;
3. an in-memory journal implementation for deterministic local use and tests;
4. deterministic performance aggregation over supplied journal entries.

The journal is a record of completed trade outcomes. It does not create broker exits, infer missing prices, or alter execution state.

## Trade Journal Contract

A `TradeJournalEntry` contains:

- `journal_id`
- `decision_id`
- `execution_id`
- `strategy_version`
- `symbol`
- `direction`
- `quantity`
- `entry_price`
- `exit_price`
- `opened_at`
- `closed_at`
- `realized_pnl`

`realized_pnl` is the canonical net realized result supplied by the journal producer. MS-0.9 does not reconstruct it from prices.

Entries must be immutable and must use timezone-aware timestamps. `closed_at` must not precede `opened_at`. Quantity must be positive.

## Performance Metrics

For a supplied deterministic sequence of completed journal entries, MS-0.9 calculates:

- total trades;
- winning trades;
- losing trades;
- breakeven trades;
- win rate;
- gross profit;
- gross loss;
- net profit/loss;
- average trade P&L;
- profit factor;
- maximum drawdown;
- maximum consecutive losses;
- expectancy per trade.

Definitions:

- win: `realized_pnl > 0`;
- loss: `realized_pnl < 0`;
- breakeven: `realized_pnl == 0`;
- win rate: winning trades / total trades;
- gross profit: sum of positive P&L;
- gross loss: absolute sum of negative P&L;
- net P&L: sum of all realized P&L;
- average trade P&L: net P&L / total trades;
- profit factor: gross profit / gross loss when gross loss is non-zero; otherwise undefined;
- maximum drawdown: largest peak-to-trough decline of the cumulative realized-P&L curve, starting from zero;
- maximum consecutive losses: longest contiguous sequence of losing trades in chronological journal order;
- expectancy: average trade P&L.

The analytics layer does not annualize returns, calculate Sharpe ratios, estimate future performance, or infer statistical significance.

## Ordering and Determinism

Analytics sorts entries by:

1. `closed_at` ascending;
2. `journal_id` ascending as a deterministic tie-breaker.

The same input entries therefore produce the same snapshot regardless of input order.

## Authority Boundaries

- Strategy remains authoritative for qualification.
- Risk remains authoritative for risk authorization and sizing.
- Governance remains authoritative for operational permission.
- Decision remains authoritative for final decision state.
- Execution remains authoritative for execution state.
- Session Policy remains authoritative for temporal eligibility.
- Journal records completed outcomes but does not authorize or modify them.
- Analytics describes supplied outcomes but cannot modify authoritative state.

## Explicit Non-Goals

MS-0.9 does not:

- change strategy rules;
- change risk formulas or limits;
- change governance rules;
- change Decision Engine semantics;
- change execution state transitions;
- introduce broker/MT5 integration;
- infer exits or P&L from incomplete execution records;
- add AI/ML prediction;
- introduce backtest assumptions;
- introduce annualized or risk-adjusted performance metrics;
- claim that historical performance predicts future results.

## Invariants

- **I-62:** Journal entries are immutable canonical completed-trade records.
- **I-63:** Journal entries require timezone-aware timestamps and positive quantity.
- **I-64:** Realized P&L is supplied by the journal producer; analytics never reconstructs it.
- **I-65:** Analytics is deterministic under chronological ordering with journal-id tie-breaking.
- **I-66:** Analytics cannot mutate strategy, risk, governance, decision, execution, or session state.
- **I-67:** Maximum drawdown is computed from cumulative realized P&L starting at zero.
- **I-68:** Undefined profit factor is represented explicitly when gross loss is zero.
- **I-69:** No future-looking, annualized, or risk-adjusted performance claim is introduced by MS-0.9.

## Acceptance Tests

- **MS09-T-01:** valid journal entry is immutable and accepted;
- **MS09-T-02:** naive timestamps are rejected;
- **MS09-T-03:** close-before-open is rejected;
- **MS09-T-04:** non-positive quantity is rejected;
- **MS09-T-05:** journal stores and returns completed entries;
- **MS09-T-06:** entries are aggregated independently of input order;
- **MS09-T-07:** wins, losses, breakevens, and win rate are deterministic;
- **MS09-T-08:** gross profit, gross loss, and net P&L are correct;
- **MS09-T-09:** average P&L and expectancy are correct;
- **MS09-T-10:** profit factor is correct;
- **MS09-T-11:** profit factor is undefined when gross loss is zero;
- **MS09-T-12:** maximum drawdown is calculated from cumulative P&L;
- **MS09-T-13:** maximum consecutive losses is deterministic;
- **MS09-T-14:** empty journal produces a zero-count snapshot without fabricated metrics;
- **MS09-T-15:** duplicate journal IDs are rejected;
- **MS09-T-16:** analytics does not mutate the supplied journal entries;
- **MS09-T-17:** repeated calculation over the same entries is identical;
- **MS09-T-18:** no strategy/risk/governance/execution/session rules are implemented in the analytics module.
