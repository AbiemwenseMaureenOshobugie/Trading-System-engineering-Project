# Historical Replay Data Audit and Correctness Fixes

## Scope

This audit addresses defects found while attempting to replay the committed
EUR/USD historical files in `data/replay/eurusd/`. It does not change the
frozen H1/M15 strategy, setup, Risk, Governance, or Decision rules.

## Confirmed defects

1. H1 `_Candidate.zone` supplied PriceZone bounds in reverse order for both
   HIGH and LOW swings.
2. Key-Level detection supplied the LOW swing zone in reverse order.
3. `HistoricalCSVAdapter` only accepted a named-column comma-separated schema,
   while the repository fixtures are headerless tab-separated rows with six
   fields: timestamp, open, high, low, close, volume.
4. The replay pipeline called `GoverningKeyLevelEngine.select` with keyword
   arguments that do not match its canonical `GoverningKeyLevelRequest`
   interface.
5. The replay harness discarded all pre-window history before strategy
   evaluation. It now retains warm-up candles as visible history but only
   evaluates and executes at cutoffs within the requested replay window.

## Data contract

The adapter accepts canonical named columns and the repository's headerless
six-field TSV/CSV layout. A single opening timestamp is converted to a close
timestamp using the requested timeframe: H1 = 1 hour; M15 = 15 minutes.
Explicit `timestamp_close` values are validated against that duration.

Naive timestamps are not silently assumed to be UTC. The caller must supply
`timestamp_timezone` after verifying the export's timezone. The committed
README documents headerless tab-separated data but does not independently
establish the timezone. Replay windows must lie within the shared H1/M15
coverage; H1-only history before M15 begins is retained for structural warm-up.

## Preserved decisions

- TRANSITION remains distinct from established UPTREND/DOWNTREND.
- No RANGE_BREAKOUT_UP/DOWN-to-direction override is added to the replay.
- No new setup, entry, risk, session, governance, target, or execution rule is
  introduced.
- Zero trades remains a valid possible result, not proof by itself that replay
  is correct.

## Validation requirement

The full CI suite must pass on the exact PR head. A replay using the real
committed CSVs is considered timezone-valid only after the export timezone is
verified and supplied explicitly. Replay reports must retain source hashes,
the requested common window, cutoff evidence, and violation counts.
