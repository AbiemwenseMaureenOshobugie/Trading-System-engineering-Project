"""Deterministic MS-0.8 H1 directional Noise calculator."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from trading_system.domain import Direction, MarketCandle, MarketStructureState, Timeframe


class NoiseCalculator:
    """Compute mean directional H1 wick size after the latest meaningful swing."""

    VERSION = "MS-0.8"

    def compute(
        self,
        *,
        candles: tuple[MarketCandle, ...],
        structure: MarketStructureState,
        direction: Direction,
    ) -> Decimal:
        last_swing = self._last_meaningful_swing_timestamp(structure)
        if last_swing is None:
            return Decimal("0")

        qualifying = [
            candle
            for candle in candles
            if candle.timeframe is Timeframe.H1
            and candle.timestamp_close > last_swing
        ]

        if not qualifying:
            return Decimal("0")

        wick_values = [self._directional_wick(candle, direction) for candle in qualifying]
        return sum(wick_values, Decimal("0")) / Decimal(len(wick_values))

    @staticmethod
    def _last_meaningful_swing_timestamp(
        structure: MarketStructureState,
    ) -> datetime | None:
        timestamps = [
            swing.timestamp
            for swing in (*structure.meaningful_highs, *structure.meaningful_lows)
        ]
        return max(timestamps) if timestamps else None

    @staticmethod
    def _directional_wick(candle: MarketCandle, direction: Direction) -> Decimal:
        if direction is Direction.BUY:
            return min(candle.open, candle.close) - candle.low
        return candle.high - max(candle.open, candle.close)


__all__ = ["NoiseCalculator"]
