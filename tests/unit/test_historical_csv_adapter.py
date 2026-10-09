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


def test_bounded_csv_replay_runs_real_pipeline_without_future_data(tmp_path: Path):
    from decimal import Decimal
    from trading_system.backtest.local import ReplayQualificationInputs, run_historical_csv_replay

    h1 = tmp_path / "eurusd_h1.csv"
    m15 = tmp_path / "eurusd_m15.csv"
    h1.write_text(
        "timestamp_open,timestamp_close,open,high,low,close\\n"
        "2026-01-05T07:00:00Z,2026-01-05T08:00:00Z,1.1000,1.1020,1.0990,1.1010\\n"
        "2026-01-05T08:00:00Z,2026-01-05T09:00:00Z,1.1010,1.1030,1.1000,1.1020\\n"
        "2026-01-05T09:00:00Z,2026-01-05T10:00:00Z,1.1020,1.1040,1.1010,1.1030\\n",
        encoding="utf-8",
    )
    m15.write_text(
        "timestamp_open,timestamp_close,open,high,low,close\\n"
        "2026-01-05T09:00:00Z,2026-01-05T09:15:00Z,1.1020,1.1030,1.1010,1.1025\\n"
        "2026-01-05T09:15:00Z,2026-01-05T09:30:00Z,1.1025,1.1040,1.1020,1.1035\\n"
        "2026-01-05T09:30:00Z,2026-01-05T09:45:00Z,1.1035,1.1045,1.1030,1.1040\\n",
        encoding="utf-8",
    )
    qualification = ReplayQualificationInputs(
        value_per_price_unit={"EURUSD": Decimal("1")},
        spread=Decimal("0.0001"), slippage=Decimal("0.0001"),
        noise=Decimal("0.0001"), volatility_adjustment=Decimal("0.0001"),
    )
    result, pipeline = run_historical_csv_replay(
        symbol="EURUSD", h1_csv=h1, m15_csv=m15,
        start=datetime(2026, 1, 5, 7, tzinfo=UTC),
        end=datetime(2026, 1, 5, 10, tzinfo=UTC),
        initial_account_equity=Decimal("10000"),
        qualification=qualification, backtest_id="TEST-CSV-REPLAY",
    )
    assert result.backtest_id == "TEST-CSV-REPLAY"
    assert result.historical_data_source == "local_csv"
    assert result.future_data_violations == ()
    assert pipeline.trace is not None
