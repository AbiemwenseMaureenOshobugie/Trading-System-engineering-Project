# MS-0.13 — Live Market Data Adapter

## Status
Contract frozen. This specification defines the first external live market-data adapter for ASTER.

MS-0.13 introduces Twelve Data only at the adapter boundary. Strategy, Risk, Governance, Decision, Session Policy, Execution, and historical replay semantics remain unchanged.

## MD-01 — Market-data provider

Locked choice: Twelve Data.

Architecture: ASTER → MarketDataPort → TwelveDataMarketDataAdapter → Twelve Data.

Twelve Data is the first external provider because it supports historical and real-time forex data, OHLC time-series retrieval, 15-minute and 1-hour intervals, EUR/USD-style forex symbols, multiple-symbol retrieval, and explicit UTC output.

MS-0.13 implements Twelve Data first. Provider alternatives remain architecturally possible but are outside this milestone.

### Entitlement safeguard
The adapter must verify that the actual Twelve Data account can access both EURUSD and GBPUSD before the observation runner starts. Missing entitlement is a configuration/runtime failure. ASTER does not silently substitute another provider or symbol.

## MD-02 — Canonical candle-completion boundary

Locked choice: an incomplete provider observation is never converted into MarketCandle.

Twelve Data bar timestamps represent the opening time of the bar. ASTER derives the expected close boundary from the requested interval:

- M15: timestamp_close = timestamp_open + 15 minutes
- H1: timestamp_close = timestamp_open + 1 hour

A candle is eligible only when timestamp_close <= observation_cutoff_utc. The observation cutoff is the UTC clock value captured for that ingestion cycle.

No is_complete field is added to MarketCandle. The canonical domain object represents completed OHLC data only.

## MD-03 — Symbol identity and mapping

Locked choice: ASTER owns canonical symbols; the provider adapter owns provider symbols.

ASTER canonical universe: EURUSD, GBPUSD.

Twelve Data mappings: EURUSD → EUR/USD; GBPUSD → GBP/USD.

The mappings live in Twelve Data adapter configuration. Provider-specific identifiers must never leak into strategy code.

At adapter initialization/configuration: every supported canonical symbol must have a provider mapping; the provider symbol must be accessible; the provider symbol must resolve to the expected instrument; unsupported mappings fail configuration validation; there is no fallback symbol guessing.

## MD-04 — Validation and failure contract

Locked choice: fail closed. Invalid or unreliable market data never reaches strategy engines.

Ingestion boundary: provider → raw response → provider parsing → completion validation → schema validation → temporal validation → duplicate detection → ordering validation → OHLC validation → symbol/timeframe validation → UTC normalization → canonical MarketCandle.

| Condition | MS-0.13 behavior |
|---|---|
| Provider unavailable | Fail closed; no new candles published |
| Timeout/network failure | Fail closed; no new candles published |
| Authentication failure | Configuration/runtime error; no candles published |
| Rate limit | Fail closed for that cycle; no fabricated data |
| Permission failure | Fail closed |
| Malformed response | Reject response |
| Invalid OHLC | Reject candle |
| Incomplete candle | Withhold candle |
| Duplicate candle | Reject duplicate; do not publish twice |
| Out-of-order data | Preserve valid chronological records; reject an invalid sequence where ordering cannot be established safely |
| Missing expected candle | No synthetic candle |
| Stale latest candle | Observation cycle is stale/unavailable |
| Unsupported symbol | Configuration/data error |
| Unsupported timeframe | Configuration error |

ASTER will not forward-fill missing candles, copy previous candles, interpolate OHLC, fabricate zero-volume candles, silently repair malformed prices, or silently skip broken data and pretend the series is continuous.

Unknown market information remains unknown.

## MD-05 — Polling contract

Locked choice: boundary-driven REST polling. WebSocket is deferred.

The observation runner schedules ingestion cycles around expected candle-completion boundaries rather than continuously polling.

Conceptually, M15 polls occur after each 15-minute boundary and H1 polls after each hourly boundary.

Initial operational default: poll_offset = 30 seconds after expected candle close.

The polling offset is an operational configuration, not a trading rule. The runner requests the newest relevant completed candles and deduplicates them against the latest accepted canonical timestamp.

WebSocket streaming is explicitly deferred. MS-0.13 implements REST polling only.

## MD-06 — Provenance

Locked choice: preserve provider identity on the canonical candle and retrieval context in auditable ingestion metadata.

MarketCandle.source remains the canonical source identity.

Retrieval/provenance metadata preserves, at minimum, provider, provider symbol, timeframe, retrieval timestamp, observation cutoff, request context, and validation outcome.

Provider-specific retrieval details belong to the ingestion/audit boundary and do not become H1/M15 strategy semantics.

## Historical warm-up — operational contract

MS-0.13 does not introduce a hard-coded strategy lookback.

The observation runner receives an explicit configurable warm-up window, such as warmup_start/warmup_end or an equivalent duration-based configuration.

The runner requests enough data for that operational window. It does not assert that ASTER requires a fixed number of H1 candles. The existing H1 engine remains responsible for determining whether supplied history is sufficient; its existing UNCLEAR behavior remains authoritative when it cannot establish sufficient structure.

MS-0.13 therefore answers: what operational history did I request? The H1 strategy answers: is the history sufficient to establish structure?

## Final frozen contract

| ID | Decision | Locked choice |
|---|---|---|
| MD-01 | Provider | Twelve Data |
| MD-02 | Completion | Only completed candles become MarketCandle |
| MD-03 | Symbols | ASTER EURUSD / GBPUSD; adapter-owned provider mapping |
| MD-04 | Failure | Fail closed; never fabricate or silently repair market data |
| MD-05 | Polling | REST, boundary-driven polling; WebSocket deferred |
| MD-06 | Provenance | Source on canonical candle plus separate auditable ingestion/retrieval metadata |

Resulting boundary: Twelve Data → parse/completion → validation/normalization → canonical MarketCandle → existing H1/M15 strategy.

## Explicit non-goals

MS-0.13 does not introduce TradingView integration, TradingView webhooks, MT5 market-data integration, broker execution changes, live orders, AI/ML interpretation, strategy modification, new H1/M15 rules, new Risk rules, new Governance rules, new Session Policy rules, WebSocket infrastructure, or portfolio logic.

## Implementation boundary

The next MS-0.13 implementation batch may implement the adapter, validation/normalization boundary, observation runner, provenance metadata, tests, and entitlement/configuration checks against this frozen contract.

No additional methodology decision is required before that implementation batch.