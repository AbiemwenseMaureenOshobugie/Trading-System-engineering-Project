"""Tests for canonical domain contracts."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.domain import (
    Direction,
    MarketCandle,
    PriceZone,
    Regime,
    SwingKind,
    SwingPoint,
    Timeframe,
)


TIMESTAMP_OPEN = datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)
TIMESTAMP_CLOSE = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def test_market_candle_preserves_canonical_ohlc_contract() -> None:
    candle = MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=TIMESTAMP_OPEN,
        timestamp_close=TIMESTAMP_CLOSE,
        open=Decimal("1.1000"),
        high=Decimal("1.1050"),
        low=Decimal("1.0980"),
        close=Decimal("1.1030"),
        volume=Decimal("100"),
        source="test",
    )

    assert candle.symbol == "EURUSD"
    assert candle.timeframe is Timeframe.H1
    assert candle.high == Decimal("1.1050")


def test_market_candle_rejects_invalid_ohlc() -> None:
    with pytest.raises(ValueError, match="high"):
        MarketCandle(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp_open=TIMESTAMP_OPEN,
            timestamp_close=TIMESTAMP_CLOSE,
            open=Decimal("1.1000"),
            high=Decimal("1.0990"),
            low=Decimal("1.0980"),
            close=Decimal("1.1030"),
        )


def test_market_candle_rejects_naive_timestamps() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        MarketCandle(
            symbol="EURUSD",
            timeframe=Timeframe.H1,
            timestamp_open=datetime(2026, 1, 1, 9, 0),
            timestamp_close=TIMESTAMP_CLOSE,
            open=Decimal("1.1000"),
            high=Decimal("1.1050"),
            low=Decimal("1.0980"),
            close=Decimal("1.1030"),
        )


def test_price_zone_is_an_interval() -> None:
    zone = PriceZone(Decimal("1.1000"), Decimal("1.1020"))
    assert zone.lower <= zone.upper


def test_structural_and_direction_enums_are_explicit() -> None:
    swing = SwingPoint(
        timestamp=TIMESTAMP_CLOSE,
        price=Decimal("1.1050"),
        kind=SwingKind.HIGH,
    )
    assert swing.kind is SwingKind.HIGH
    assert Regime.UNCLEAR.value == "UNCLEAR"
    assert Direction.BUY.value == "BUY"
