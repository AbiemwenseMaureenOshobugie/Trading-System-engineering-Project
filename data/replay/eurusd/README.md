Add EUR/USD replay candles (H1 + M15) under data/replay/eurusd/

Tab-separated, headerless BID CSVs:
  timestamp | open | high | low | close | volume

- EURUSD60.csv — H1,  2010-09-28 07:00 to 2026-10-09 21:00
- EURUSD15.csv — M15, 2022-10-06 06:15 to 2026-10-09 21:00

Coverage differs: H1 spans ~16 years, M15 ~4 years.
Replay evaluation windows must lie within the shared H1/M15 coverage
(2022-10-06 onward). Earlier H1 candles may be retained as structural
warm-up, but must not create pre-window decisions or executions.

The stored timestamps have no explicit UTC offset. The replay adapter requires
the caller to pass the source timezone explicitly after verifying the export
settings; it must not silently interpret naive timestamps as UTC.

README.md documents layout, coverage, and provenance.
