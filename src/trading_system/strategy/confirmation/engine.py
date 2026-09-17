"""Deterministic M15 confirmation primitives for MS-0.3.

This module currently implements the corrected M15-06 swing primitive. It does
not select a governing Key Level, calculate risk, authorize execution, or add
trading conditions.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from trading_system.domain import MarketCandle, SwingKind, SwingPoint, Timeframe

CONFIRMATION_VERSION = "MS-0.3"


@dataclass(frozen=True, slots=True)
class ConfirmedM15Swing:
    """A confirmed M15 swing and the close at which it became confirmed."""

    swing: SwingPoint
    confirmed_at: datetime


class M15SwingDetector:
    """Implement the frozen three-candle M15-06 swing definition.

    A candidate is formed from three completed M15 candles: left, middle and
    right. The candidate becomes confirmed when the right candle closes.
    """

    def confirm(
        self, *, candles: Sequence[MarketCandle]
    ) -> Sequence[ConfirmedM15Swing]:
        eligible = self._eligible_candles(candles)
        confirmed: list[ConfirmedM15Swing] = []

        for index in range(1, len(eligible) - 1):
            left = eligible[index - 1]
            middle = eligible[index]
            right = eligible[index + 1]

            is_high = (
                middle.high > left.high
                and middle.high > right.high
                and middle.low > right.low
            )
            is_low = (
                middle.low < left.low
                and middle.low < right.low
                and middle.high < right.high
            )

            # A candle cannot qualify as both a high and a low under the
            # corrected definition. Keep the explicit guard as a defensive
            # domain invariant rather than inventing a tie-break rule.
            if is_high and is_low:
                continue
            if is_high:
                confirmed.append(
                    ConfirmedM15Swing(
                        swing=SwingPoint(
                            timestamp=middle.timestamp_open,
                            price=middle.high,
                            kind=SwingKind.HIGH,
                        ),
                        confirmed_at=right.timestamp_close,
                    )
                )
            elif is_low:
                confirmed.append(
                    ConfirmedM15Swing(
                        swing=SwingPoint(
                            timestamp=middle.timestamp_open,
                            price=middle.low,
                            kind=SwingKind.LOW,
                        ),
                        confirmed_at=right.timestamp_close,
                    )
                )

        return tuple(confirmed)

    @staticmethod
    def _eligible_candles(candles: Sequence[MarketCandle]) -> list[MarketCandle]:
        eligible = [c for c in candles if c.timeframe is Timeframe.M15]
        return sorted(eligible, key=lambda candle: candle.timestamp_open)


__all__ = ["CONFIRMATION_VERSION", "ConfirmedM15Swing", "M15SwingDetector"]
