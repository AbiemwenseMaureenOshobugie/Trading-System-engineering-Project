"""Tests for the deterministic MS-0.8 Noise calculator."""

from datetime import datetime, timezone
from decimal import Decimal

from trading_system.domain import (
    Direction,
    MarketCandle,
    MarketStructureState,
    Regime,
    SwingKind,
    SwingPoint,
    Timeframe,
)
from trading_system.market_observation import NoiseCalculator

TS = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)


def candle(
    *,
    close_hour: int,
    open_price: str,
    high: str,
    low: str,
    close: str,
    timeframe: Timeframe = Timeframe.H1,
) -> MarketCandle:
    start = TS.replace(hour=close_hour - 1)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=timeframe,
        timestamp_open=start,
        timestamp_close=TS.replace(hour=close_hour),
        open=Decimal(open_price),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        source="test",
    )


def structure(*swing_hours: int) -> MarketStructureState:
    swings = tuple(
        SwingPoint(
            timestamp=TS.replace(hour=hour),
            price=Decimal("1.1000"),
            kind=SwingKind.HIGH if index % 2 == 0 else SwingKind.LOW,
        )
        for index, hour in enumerate(swing_hours)
    )
    return MarketStructureState(
        regime=Regime.UNCLEAR,
        structure_version="MS-0.1A",
        meaningful_highs=tuple(s for s in swings if s.kind is SwingKind.HIGH),
        meaningful_lows=tuple(s for s in swings if s.kind is SwingKind.LOW),
        controlling_level=None,
        range_upper_boundary=None,
        range_lower_boundary=None,
        structural_events=(),
        evaluated_at=TS,
    )


def test_buy_uses_mean_lower_wick_after_latest_meaningful_swing():
    result = NoiseCalculator().compute(
        candles=(
            candle(close_hour=10, open_price="1.105", high="1.110", low="1.100", close="1.108"),
            candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),
            candle(close_hour=12, open_price="1.110", high="1.115", low="1.107", close="1.109"),
            candle(close_hour=13, open_price="1.109", high="1.113", low="1.108", close="1.112"),
        ),
        structure=structure(10),
        direction=Direction.BUY,
    )
    assert result == Decimal("0.003")


def test_sell_uses_mean_upper_wick_after_latest_meaningful_swing():
    result = NoiseCalculator().compute(
        candles=(
            candle(close_hour=10, open_price="1.105", high="1.110", low="1.100", close="1.108"),
            candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),
            candle(close_hour=12, open_price="1.110", high="1.115", low="1.107", close="1.109"),
            candle(close_hour=13, open_price="1.109", high="1.113", low="1.108", close="1.112"),
        ),
        structure=structure(10),
        direction=Direction.SELL,
    )
    assert result == Decimal("0.003")


def test_swing_candle_is_excluded_and_latest_swing_controls_window():
    result = NoiseCalculator().compute(
        candles=(
            candle(close_hour=10, open_price="1.105", high="1.110", low="1.100", close="1.108"),
            candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),
            candle(close_hour=12, open_price="1.110", high="1.115", low="1.107", close="1.109"),
        ),
        structure=structure(10, 11),
        direction=Direction.BUY,
    )
    assert result == Decimal("0.002")


def test_empty_window_returns_zero():
    result = NoiseCalculator().compute(
        candles=(candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),),
        structure=structure(11),
        direction=Direction.BUY,
    )
    assert result == Decimal("0")


def test_no_meaningful_swing_returns_zero():
    result = NoiseCalculator().compute(
        candles=(candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),),
        structure=MarketStructureState(
            regime=Regime.UNCLEAR,
            structure_version="MS-0.1A",
            meaningful_highs=(),
            meaningful_lows=(),
            controlling_level=None,
            range_upper_boundary=None,
            range_lower_boundary=None,
            structural_events=(),
            evaluated_at=TS,
        ),
        direction=Direction.BUY,
    )
    assert result == Decimal("0")


def test_non_h1_candles_are_excluded():
    result = NoiseCalculator().compute(
        candles=(
            candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),
            candle(close_hour=12, open_price="1.110", high="1.120", low="1.100", close="1.115", timeframe=Timeframe.M15),
        ),
        structure=structure(10),
        direction=Direction.BUY,
    )
    assert result == Decimal("0.002")


def test_candle_order_does_not_change_result():
    candles = (
        candle(close_hour=11, open_price="1.108", high="1.112", low="1.104", close="1.110"),
        candle(close_hour=12, open_price="1.110", high="1.115", low="1.107", close="1.109"),
    )
    engine = NoiseCalculator()
    assert engine.compute(candles=candles, structure=structure(10), direction=Direction.BUY) == engine.compute(
        candles=tuple(reversed(candles)), structure=structure(10), direction=Direction.BUY
    )


def test_noise_port_is_runtime_compatible():
    from trading_system.application import NoiseCalculatorPort
    assert isinstance(NoiseCalculator(), NoiseCalculatorPort)
