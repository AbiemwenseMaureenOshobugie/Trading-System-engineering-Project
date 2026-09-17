"""Tests for the corrected MS-0.3 M15-06 swing definition."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.domain import MarketCandle, SwingKind, Timeframe
from trading_system.strategy.confirmation import M15SwingDetector

UTC = timezone.utc
BASE = datetime(2026, 1, 1, tzinfo=UTC)


def candle(i: int, open_: str, high: str, low: str, close: str) -> MarketCandle:
    start = BASE + timedelta(minutes=15 * i)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.M15,
        timestamp_open=start,
        timestamp_close=start + timedelta(minutes=15),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def test_high_requires_all_three_conditions() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
            candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
            candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
        )
    )
    assert len(swings) == 1
    assert swings[0].swing.kind is SwingKind.HIGH
    assert swings[0].swing.price == Decimal("1.1100")
    assert swings[0].confirmed_at == BASE + timedelta(minutes=45)


def test_high_is_rejected_without_right_lower_low() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
            candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
            candle(2, "1.1080", "1.1090", "1.1020", "1.1050"),
        )
    )
    assert swings == ()


def test_high_is_rejected_without_middle_high_above_right_high() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
            candle(1, "1.1030", "1.1090", "1.1010", "1.1080"),
            candle(2, "1.1080", "1.1100", "1.1000", "1.1020"),
        )
    )
    assert swings == ()


def test_low_requires_all_three_conditions() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1050", "1.1080", "1.1000", "1.1020"),
            candle(1, "1.1020", "1.1030", "1.0950", "1.0970"),
            candle(2, "1.0970", "1.1050", "1.0960", "1.1030"),
        )
    )
    assert len(swings) == 1
    assert swings[0].swing.kind is SwingKind.LOW
    assert swings[0].swing.price == Decimal("1.0950")
    assert swings[0].confirmed_at == BASE + timedelta(minutes=45)


def test_low_is_rejected_without_right_higher_high() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1050", "1.1080", "1.1000", "1.1020"),
            candle(1, "1.1020", "1.1030", "1.0950", "1.0970"),
            candle(2, "1.0970", "1.1020", "1.0960", "1.1030"),
        )
    )
    assert swings == ()


def test_low_is_rejected_without_middle_low_below_right_low() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1050", "1.1080", "1.1000", "1.1020"),
            candle(1, "1.1020", "1.1030", "1.0960", "1.0970"),
            candle(2, "1.0970", "1.1050", "1.0950", "1.1030"),
        )
    )
    assert swings == ()


def test_right_candle_close_is_confirmation_time() -> None:
    swings = M15SwingDetector().confirm(
        candles=(
            candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
            candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
            candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
        )
    )
    assert swings[0].confirmed_at == BASE + timedelta(minutes=45)


def test_only_completed_m15_candles_are_consumed() -> None:
    candles = (
        candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
        candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
        candle(3, "1.1020", "1.1040", "1.0990", "1.1030"),
    )
    swings = M15SwingDetector().confirm(candles=candles)
    assert len(swings) == 1


def test_non_m15_candles_are_ignored() -> None:
    h1 = MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=BASE,
        timestamp_close=BASE + timedelta(hours=1),
        open=Decimal("1.1000"),
        high=Decimal("1.2000"),
        low=Decimal("1.0900"),
        close=Decimal("1.1500"),
    )
    m15 = (
        candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
        candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    )
    swings = M15SwingDetector().confirm(candles=(h1, *m15))
    assert len(swings) == 1


def test_results_are_deterministic() -> None:
    candles = (
        candle(0, "1.1000", "1.1050", "1.0980", "1.1030"),
        candle(1, "1.1030", "1.1100", "1.1010", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    )
    engine = M15SwingDetector()
    assert engine.confirm(candles=candles) == engine.confirm(candles=candles)
