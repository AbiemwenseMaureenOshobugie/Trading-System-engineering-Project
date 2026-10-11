"""Actual committed EURUSD history: one-hour replay plumbing validation.

This is a deterministic integration smoke test, not a performance backtest.
The committed files contain six fields (timestamp, OHLC, volume) and no spread
field, so zero costs are used only to exercise the full pipeline; the result
must not be interpreted as realistic profitability or execution performance.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from trading_system.backtest.local import (
    ReplayQualificationInputs,
    run_historical_csv_replay,
)

UTC = timezone.utc
DATA = Path(__file__).resolve().parents[1] / "data" / "replay" / "eurusd"


def _metadata(path: Path) -> dict[str, object]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return {
        "path": str(path.relative_to(DATA.parents[1])),
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "rows": len(lines),
        "first_row": lines[0],
        "last_row": lines[-1],
        "field_counts": sorted({len(line.split("\t")) for line in lines}),
    }


def test_committed_eurusd_files_replay_on_real_utc_data() -> None:
    h1_path = DATA / "EURUSD60.csv"
    m15_path = DATA / "EURUSD15.csv"
    assert h1_path.is_file()
    assert m15_path.is_file()

    # Restrict evaluated cutoffs to the final shared UTC hour while preserving
    # all earlier candles as H1/M15 structural warm-up history.
    start = datetime(2026, 10, 9, 20, 0, tzinfo=UTC)
    end = datetime(2026, 10, 9, 21, 0, tzinfo=UTC)

    qualification = ReplayQualificationInputs(
        value_per_price_unit={"EURUSD": Decimal("1")},
        spread=Decimal("0"),
        slippage=Decimal("0"),
        noise=Decimal("0"),
        volatility_adjustment=Decimal("0"),
    )
    result, pipeline = run_historical_csv_replay(
        symbol="EURUSD",
        h1_csv=h1_path,
        m15_csv=m15_path,
        start=start,
        end=end,
        initial_account_equity=Decimal("10000"),
        qualification=qualification,
        backtest_id="EURUSD-REAL-DATA-UTC-20261009-20Z",
        timestamp_timezone=UTC,
    )

    report = {
        "validation_kind": "full-pipeline integration smoke test; not a performance backtest",
        "timezone": "UTC (user-confirmed export timezone)",
        "transaction_costs": "zero diagnostic assumptions; source files contain no spread column",
        "window_utc": {"start": start.isoformat(), "end": end.isoformat()},
        "inputs": [_metadata(h1_path), _metadata(m15_path)],
        "replay": {
            "backtest_id": result.backtest_id,
            "historical_data_version": result.historical_data_version,
            "strategy_candidates": result.strategy_candidates,
            "valid_decisions": result.valid_decisions,
            "wait_decisions": result.wait_decisions,
            "risk_rejections": result.risk_rejections,
            "governance_blocks": result.governance_blocks,
            "executed_entries": result.executed_entries,
            "completed_trades": result.completed_trade_count,
            "future_data_violations": list(result.future_data_violations),
            "ordering_violations": list(result.ordering_violations),
            "ambiguous_executions": result.ambiguous_executions,
            "pipeline_trace_records": len(pipeline.trace),
        },
    }
    print("ASTER_REAL_DATA_REPLAY_REPORT=" + json.dumps(report, sort_keys=True))

    assert result.start_timestamp == start
    assert result.end_timestamp == end
    assert result.historical_data_source == "local_csv"
    assert len(result.historical_data_version) == 64
    assert result.future_data_violations == ()
    assert result.ordering_violations == ()
