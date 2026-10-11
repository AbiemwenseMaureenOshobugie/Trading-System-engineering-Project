Add EUR/USD replay candles (H1 + M15) under data/replay/eurusd/

Tab-separated, headerless BID CSVs:
  timestamp | open | high | low | close | volume

- EURUSD60.csv — H1,  2010-09-28 07:00 to 2026-10-09 21:00
- EURUSD15.csv — M15, 2022-10-06 06:15 to 2026-10-09 21:00

Coverage differs: H1 spans ~16 years, M15 ~4 years.
Replay windows must be drawn from the intersection
(2022-10-06 onward) for combined H1 + M15 evaluation.

README.md documents layout, coverage, and provenance.
