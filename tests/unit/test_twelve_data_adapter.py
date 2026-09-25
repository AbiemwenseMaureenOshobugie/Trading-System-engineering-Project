"""MS-0.13 Twelve Data adapter contract tests."""

from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Mapping

import pytest

from trading_system.adapters.twelve_data import (
    TwelveDataAdapterConfig,
    TwelveDataMarketDataAdapter,
    CompletionBoundary,
    CompletionResult,
    SymbolMapper,
    CandleValidator,
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
    IngestionRecord,
    IngestionOutcome,
    PollingSchedule,
)
from trading_system.domain import MarketCandle, Timeframe

TS = datetime(2026, 9, 1, 10, 0, tzinfo=timezone.utc)

# Test configuration
TEST_CONFIG = TwelveDataAdapterConfig(
    api_key="test_key",
    symbol_map={"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD"},
    base_url="https://api.twelvedata.com",
    timeout_seconds=10.0,
    poll_offset_seconds=30,
)


class FakeTwelveDataGateway:
    """Fake HTTP gateway for testing (no live API)."""

    def __init__(
        self,
        *,
        status: str = "ok",
        values: list[dict] | None = None,
        error_code: str | None = None,
        error_message: str = "fake error",
    ) -> None:
        self.status = status
        self.values = values or []
        self.error_code = error_code
        self.error_message = error_message
        self.requests: list[dict] = []

    def get(self, url: str, params: Mapping[str, str], timeout: float) -> dict:
        self.requests.append({"url": url, "params": params})
        if self.error_code:
            return {"status": "error", "message": self.error_message, "code": self.error_code}
        return {"status": self.status, "values": self.values}


def make_adapter(fake_gateway: FakeTwelveDataGateway) -> TwelveDataMarketDataAdapter:
    return TwelveDataMarketDataAdapter(
        config=TEST_CONFIG,
        gateway=fake_gateway,
        clock=lambda: TS,
    )


# MS13-T-01: Adapter implements MarketDataPort
def test_adapter_implements_market_data_port():
    from trading_system.application.ports import MarketDataPort
    fake = FakeTwelveDataGateway()
    adapter = make_adapter(fake)
    assert isinstance(adapter, MarketDataPort)


# MS13-T-02: Incomplete candles are withheld
def test_incomplete_candles_withheld():
    # 9:46 is 14 minutes before 10:00 - expected close 10:01 > 10:00, so INCOMPLETE
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:46:00",
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 0  # Incomplete - withheld


# MS13-T-03: Only completed candles become MarketCandle
def test_only_completed_candles_become_market_candle():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:30:00",  # 30 min before TS - complete
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }, {
            "datetime": "2026-09-01 09:46:00",  # 14 min before TS - incomplete
            "open": "1.1002", "high": "1.1008", "low": "1.1000", "close": "1.1005", "volume": "150"
        }]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 1
    assert candles[0].timestamp_open == datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)
    assert candles[0].source == "twelve_data"


# MS13-T-04: Symbol mapping is provider-owned
def test_symbol_mapping_provider_owned():
    fake = FakeTwelveDataGateway()
    adapter = make_adapter(fake)
    assert adapter._mapper.to_provider("EURUSD") == "EUR/USD"
    assert adapter._mapper.to_provider("GBPUSD") == "GBP/USD"
    with pytest.raises(KeyError):
        adapter._mapper.to_provider("USDJPY")


# MS13-T-05: Provider identifiers do not leak into strategy
def test_provider_identifiers_do_not_leak():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:30:00",
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 1
    assert candles[0].symbol == "EURUSD"  # Canonical symbol
    assert candles[0].source == "twelve_data"  # Canonical source identity
    assert "EUR/USD" not in str(candles[0])  # Provider symbol not in canonical object


# MS13-T-06: Fail-closed on provider unavailable
def test_fail_closed_provider_unavailable():
    fake = FakeTwelveDataGateway(error_code="NETWORK_ERROR", error_message="connection failed")
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 0  # Fail closed - no candles


# MS13-T-07: Fail-closed on rate limit
def test_fail_closed_rate_limit():
    fake = FakeTwelveDataGateway(
        status="error",
        values=[],
        error_code="HTTP_429",
        error_message="rate limit exceeded"
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 0


# MS13-T-08: Fail-closed on invalid OHLC
def test_fail_closed_invalid_ohlc():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:30:00",
            "open": "1.1000", "high": "1.0990", "low": "1.0995", "close": "1.1002", "volume": "100"  # high < open
        }]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 0  # Invalid OHLC rejected


# MS13-T-09: Duplicate candle rejected
def test_duplicate_candle_rejected():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[
            {"datetime": "2026-09-01 09:30:00", "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"},
            {"datetime": "2026-09-01 09:30:00", "open": "1.1001", "high": "1.1006", "low": "1.0996", "close": "1.1003", "volume": "100"},
        ]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 1  # Duplicate rejected


# MS13-T-10: Missing candle not fabricated
def test_missing_candle_not_fabricated():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:00:00",
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }]  # Missing 09:15, 09:30
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 1  # Only the one provided, no synthetic candles


# MS13-T-11: Boundary-driven polling schedule
def test_boundary_driven_polling_schedule():
    schedule = PollingSchedule(poll_offset_seconds=30)
    boundary = CompletionBoundary.from_cutoff(TS)
    next_poll = schedule.next_poll_time(Timeframe.M15, TS)
    # Next M15 boundary after 10:00 is 10:15, +30s = 10:15:30
    expected = datetime(2026, 9, 1, 10, 15, 30, tzinfo=timezone.utc)
    assert next_poll == expected


# MS13-T-12: Warm-up window is operational configuration
def test_warmup_window_operational_config():
    config = TwelveDataAdapterConfig(
        api_key="test",
        symbol_map={"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD"},
        warmup_start="2026-01-01T00:00:00Z",
        warmup_end="2026-01-02T00:00:00Z",
    )
    assert config.warmup_start == "2026-01-01T00:00:00Z"
    assert config.warmup_end == "2026-01-02T00:00:00Z"


# MS13-T-13: Provenance record preserved
def test_provenance_record_preserved():
    from trading_system.adapters.twelve_data.provenance import IngestionRecord, IngestionOutcome
    record = IngestionRecord(
        provider="twelve_data",
        provider_symbol="EUR/USD",
        canonical_symbol="EURUSD",
        timeframe=Timeframe.M15,
        retrieval_timestamp=TS,
        observation_cutoff=TS,
        request_context={"interval": "15min"},
        validation_outcome=IngestionOutcome.SUCCESS,
        candles_accepted=5,
        candles_rejected=0,
        candles_withheld_incomplete=2,
    )
    assert record.provider == "twelve_data"
    assert record.canonical_symbol == "EURUSD"
    assert record.provider_symbol == "EUR/USD"
    assert record.is_success


# MS13-T-14: Entitlement checked at initialization
def test_entitlement_checked_at_initialization():
    fake = FakeTwelveDataGateway()
    adapter = make_adapter(fake)
    # Should not raise - fake gateway returns ok
    adapter.verify_entitlement()
    assert len(fake.requests) == 2  # One for each symbol


# MS13-T-15: No WebSocket dependency
def test_no_websocket_dependency():
    import inspect
    source = inspect.getsource(TwelveDataMarketDataAdapter)
    assert "websocket" not in source.lower()
    assert "WebSocket" not in source
    assert "ws://" not in source
    assert "wss://" not in source


# MS13-T-16: UTC normalization enforced
def test_utc_normalization_enforced():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:30:00",  # UTC
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }]
    )
    adapter = make_adapter(fake)
    candles = adapter.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles) == 1
    assert candles[0].timestamp_open.tzinfo == timezone.utc
    assert candles[0].timestamp_close.tzinfo == timezone.utc


# MS13-T-17: Deterministic output
def test_deterministic_output():
    fake = FakeTwelveDataGateway(
        status="ok",
        values=[{
            "datetime": "2026-09-01 09:30:00",
            "open": "1.1000", "high": "1.1005", "low": "1.0995", "close": "1.1002", "volume": "100"
        }]
    )
    adapter1 = make_adapter(fake)
    adapter2 = make_adapter(fake)
    candles1 = adapter1.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    candles2 = adapter2.get_candles(symbol="EURUSD", timeframe=Timeframe.M15, start=TS - timedelta(hours=1), end=TS)
    assert len(candles1) == len(candles2) == 1
    assert candles1[0] == candles2[0]


# MS13-T-18: No strategy semantics changed
def test_no_strategy_semantics_changed():
    # Verify that domain models and ports are unchanged
    from trading_system.domain import MarketCandle, Timeframe
    from trading_system.application.ports import MarketDataPort
    
    # MarketCandle should not have new fields
    candle = MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        timestamp_open=TS - timedelta(minutes=15),
        timestamp_close=TS,
        open=Decimal("1.1000"),
        high=Decimal("1.1005"),
        low=Decimal("1.0995"),
        close=Decimal("1.1002"),
        volume=Decimal("100"),
        source="twelve_data",
    )
    # Should not have is_complete field
    assert not hasattr(candle, "is_complete")
    # Should not have provider_symbol field
    assert not hasattr(candle, "provider_symbol")
    
    # MarketDataPort should not have changed
    import inspect
    sig = inspect.signature(MarketDataPort.get_candles)
    params = list(sig.parameters.keys())
    assert params == ["self", "symbol", "timeframe", "start", "end"]


# Additional tests for CompletionBoundary
def test_completion_boundary_m15():
    boundary = CompletionBoundary.from_cutoff(TS)
    ts = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)  # 30 min before -> close at 9:45 <= 10:00, COMPLETE
    assert boundary.is_complete(ts, Timeframe.M15) == CompletionResult.COMPLETE
    ts = datetime(2026, 9, 1, 9, 46, tzinfo=timezone.utc)  # 14 min before -> close at 10:01 > 10:00, INCOMPLETE
    assert boundary.is_complete(ts, Timeframe.M15) == CompletionResult.INCOMPLETE
    ts = datetime(2026, 9, 1, 9, 45, tzinfo=timezone.utc)  # 15 min before -> close at 10:00 <= 10:00, COMPLETE
    assert boundary.is_complete(ts, Timeframe.M15) == CompletionResult.COMPLETE


def test_completion_boundary_h1():
    boundary = CompletionBoundary.from_cutoff(TS)
    ts = datetime(2026, 9, 1, 8, 0, tzinfo=timezone.utc)  # 2 hours before -> close at 9:00 <= 10:00, COMPLETE
    assert boundary.is_complete(ts, Timeframe.H1) == CompletionResult.COMPLETE
    ts = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)  # 30 min before -> close at 10:30 > 10:00, INCOMPLETE
    assert boundary.is_complete(ts, Timeframe.H1) == CompletionResult.INCOMPLETE
    ts = datetime(2026, 9, 1, 9, 0, tzinfo=timezone.utc)  # 1 hour before -> close at 10:00 <= 10:00, COMPLETE
    assert boundary.is_complete(ts, Timeframe.H1) == CompletionResult.COMPLETE


def test_completion_boundary_invalid_timestamp():
    boundary = CompletionBoundary.from_cutoff(TS)
    ts = datetime(2026, 9, 1, 9, 30)  # Naive
    assert boundary.is_complete(ts, Timeframe.M15) == CompletionResult.INVALID_TIMESTAMP


def test_symbol_mapper_config_validation():
    # Valid
    SymbolMapper.from_config({"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD"})
    # Duplicate provider symbols
    with pytest.raises(ValueError, match="duplicate provider symbols"):
        SymbolMapper.from_config({"EURUSD": "EUR/USD", "GBPUSD": "EUR/USD"})
    # Empty provider symbol
    with pytest.raises(ValueError, match="must not be empty"):
        SymbolMapper.from_config({"EURUSD": "", "GBPUSD": "GBP/USD"})


def test_config_validation():
    # Valid
    TwelveDataAdapterConfig(api_key="key", symbol_map={"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD"})
    # Missing api_key
    with pytest.raises(ValueError, match="api_key is required"):
        TwelveDataAdapterConfig(api_key="", symbol_map={"EURUSD": "EUR/USD", "GBPUSD": "GBP/USD"})
    # Missing required symbols
    with pytest.raises(ValueError, match="missing required canonical symbols"):
        TwelveDataAdapterConfig(api_key="key", symbol_map={"EURUSD": "EUR/USD"})
    # Empty symbol_map
    with pytest.raises(ValueError, match="symbol_map must contain at least one mapping"):
        TwelveDataAdapterConfig(api_key="key", symbol_map={})


def test_validation_pipeline():
    observed = set()
    validator = CandleValidator(
        canonical_symbol="EURUSD",
        timeframe=Timeframe.M15,
        observed_timestamps=observed,
    )
    ts = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)
    result = validator.validate(
        provider_symbol="EUR/USD",
        timestamp_open=ts,
        timestamp_close=ts + timedelta(minutes=15),
        open_price=Decimal("1.1000"),
        high_price=Decimal("1.1005"),
        low_price=Decimal("1.0995"),
        close_price=Decimal("1.1002"),
        volume=Decimal("100"),
        retrieval_timestamp=TS,
        observation_cutoff=TS,
    )
    assert result.is_valid
    assert result.candle is not None
    assert result.candle.symbol == "EURUSD"
    assert result.candle.timeframe == Timeframe.M15
    assert ts in observed


def test_validation_invalid_ohlc():
    observed = set()
    validator = CandleValidator(
        canonical_symbol="EURUSD",
        timeframe=Timeframe.M15,
        observed_timestamps=observed,
    )
    ts = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)
    result = validator.validate(
        provider_symbol="EUR/USD",
        timestamp_open=ts,
        timestamp_close=ts + timedelta(minutes=15),
        open_price=Decimal("1.1000"),
        high_price=Decimal("1.0990"),  # Invalid: high < open
        low_price=Decimal("1.0995"),
        close_price=Decimal("1.1002"),
        volume=Decimal("100"),
        retrieval_timestamp=TS,
        observation_cutoff=TS,
    )
    assert not result.is_valid
    assert any(e.code == ValidationErrorCode.INVALID_OHLC for e in result.errors)


def test_validation_duplicate():
    observed = {datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)}
    validator = CandleValidator(
        canonical_symbol="EURUSD",
        timeframe=Timeframe.M15,
        observed_timestamps=observed,
    )
    ts = datetime(2026, 9, 1, 9, 30, tzinfo=timezone.utc)
    result = validator.validate(
        provider_symbol="EUR/USD",
        timestamp_open=ts,
        timestamp_close=ts + timedelta(minutes=15),
        open_price=Decimal("1.1000"),
        high_price=Decimal("1.1005"),
        low_price=Decimal("1.0995"),
        close_price=Decimal("1.1002"),
        volume=Decimal("100"),
        retrieval_timestamp=TS,
        observation_cutoff=TS,
    )
    assert not result.is_valid
    assert any(e.code == ValidationErrorCode.DUPLICATE_CANDLE for e in result.errors)


def test_validation_utc_normalization():
    observed = set()
    validator = CandleValidator(
        canonical_symbol="EURUSD",
        timeframe=Timeframe.M15,
        observed_timestamps=observed,
    )
    ts = datetime(2026, 9, 1, 9, 30)  # Naive
    result = validator.validate(
        provider_symbol="EUR/USD",
        timestamp_open=ts,
        timestamp_close=ts + timedelta(minutes=15),
        open_price=Decimal("1.1000"),
        high_price=Decimal("1.1005"),
        low_price=Decimal("1.0995"),
        close_price=Decimal("1.1002"),
        volume=Decimal("100"),
        retrieval_timestamp=TS,
        observation_cutoff=TS,
    )
    assert not result.is_valid
    assert any(e.code == ValidationErrorCode.UTC_NORMALIZATION_FAILURE for e in result.errors)


def test_ingestion_batch():
    from trading_system.adapters.twelve_data.provenance import IngestionBatch
    records = [
        IngestionRecord(
            provider="twelve_data",
            provider_symbol="EUR/USD",
            canonical_symbol="EURUSD",
            timeframe=Timeframe.M15,
            retrieval_timestamp=TS,
            observation_cutoff=TS,
            request_context={},
            validation_outcome=IngestionOutcome.SUCCESS,
            candles_accepted=5,
            candles_rejected=1,
            candles_withheld_incomplete=2,
        ),
        IngestionRecord(
            provider="twelve_data",
            provider_symbol="GBP/USD",
            canonical_symbol="GBPUSD",
            timeframe=Timeframe.M15,
            retrieval_timestamp=TS,
            observation_cutoff=TS,
            request_context={},
            validation_outcome=IngestionOutcome.SUCCESS,
            candles_accepted=3,
            candles_rejected=0,
            candles_withheld_incomplete=1,
        ),
    ]
    batch = IngestionBatch(
        cycle_id="test-1",
        start_time=TS,
        end_time=TS + timedelta(seconds=10),
        records=tuple(records),
    )
    assert batch.total_accepted == 8
    assert batch.total_rejected == 1
    assert batch.total_withheld == 3
    assert batch.all_success