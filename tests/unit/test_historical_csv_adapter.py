from datetime import datetime, timezone
from pathlib import Path
import pytest
from trading_system.backtest.local import HistoricalCSVAdapter, HistoricalCSVError
from trading_system.domain import Timeframe

UTC = timezone.utc

def test_loads_and_fingerprints_historical_csv(tmp_path: Path):
    path = tmp_path / "eurusd.csv"
    path.write_text(
        "timestamp_open,timestamp_close,open,high,low,close,volume\n"
        "2026-01-01T00:00:00Z,2026-01-01T01:00:00Z,1.10,1.12,1.09,1.11,10\n",
        encoding="utf-8",
    )
    candles = HistoricalCSVAdapter.load(
        path=path, symbol="EURUSD", timeframe=Timeframe.H1,
        start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert len(candles) == 1
    assert candles[0].source.startswith("csv:")
    assert candles[0].timestamp_close == datetime(2026, 1, 1, 1, tzinfo=UTC)

def test_rejects_duplicate_candle_timestamp(tmp_path: Path):
    path = tmp_path / "duplicates.csv"
    row = "2026-01-01T00:00:00Z,2026-01-01T01:00:00Z,1.10,1.12,1.09,1.11\n"
    path.write_text("timestamp_open,timestamp_close,open,high,low,close\n" + row + row, encoding="utf-8")
    with pytest.raises(HistoricalCSVError, match="duplicate"):
        HistoricalCSVAdapter.load(
            path=path, symbol="EURUSD", timeframe=Timeframe.H1,
            start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 1, 2, tzinfo=UTC),
        )

def test_rejects_missing_columns(tmp_path: Path):
    path = tmp_path / "bad.csv"
    path.write_text("timestamp_open,open,high,low,close\n", encoding="utf-8")
    with pytest.raises(HistoricalCSVError, match="missing columns"):
        HistoricalCSVAdapter.load(
            path=path, symbol="EURUSD", timeframe=Timeframe.H1,
            start=datetime(2026, 1, 1, tzinfo=UTC), end=datetime(2026, 1, 2, tzinfo=UTC),
        )
