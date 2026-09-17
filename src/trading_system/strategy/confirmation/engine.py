"""Deterministic MS-0.3 M15 confirmation engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha256
from typing import Sequence

from trading_system.application.ports import ConfirmationEnginePort
from trading_system.domain import (
    ConfirmationSequence,
    ConfirmationType,
    Direction,
    KeyLevel,
    MarketCandle,
    MarketStructureState,
    Regime,
    SwingKind,
    Timeframe,
)

CONFIRMATION_VERSION = "MS-0.3"


@dataclass(frozen=True, slots=True)
class _M15Swing:
    candle: MarketCandle
    kind: SwingKind


class M15ConfirmationEngine(ConfirmationEnginePort):
    """Evaluate deterministic CP-1 confirmation in an established H1 thesis."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
        key_levels: Sequence[KeyLevel],
    ) -> Sequence[ConfirmationSequence]:
        m15 = self._completed_m15(candles)
        direction = self._h1_direction(structure)
        if direction is None or not m15 or not key_levels:
            return ()

        swings = self._confirmed_swings(m15)
        opposing = self._most_recent_opposing_swing(swings, direction)
        if opposing is None:
            return ()

        breakout_index = self._find_breakout(m15, opposing, direction)
        if breakout_index is None:
            return ()

        broken_level = opposing.candle.high if direction is Direction.BUY else opposing.candle.low
        retest_index = self._find_retest(m15, breakout_index, broken_level, direction)
        if retest_index is None:
            return ()

        rejection = m15[retest_index]
        if not self._is_rejection(rejection, direction):
            return ()

        if not self._structure_aligns(m15, retest_index, direction):
            return ()

        trigger_index = retest_index + 1
        if trigger_index >= len(m15):
            return (self._pending_cp1(direction, key_levels, breakout_index, retest_index),)

        trigger = m15[trigger_index]
        rejection_extreme = rejection.high if direction is Direction.BUY else rejection.low
        triggered = (
            trigger.close > rejection_extreme
            if direction is Direction.BUY
            else trigger.close < rejection_extreme
        )
        if not triggered:
            return ()

        key_level = self._select_key_level_for_reference(key_levels)
        return (
            ConfirmationSequence(
                setup_id=self._setup_id(direction, key_level, trigger),
                confirmation_type=ConfirmationType.CP1,
                direction=direction,
                setup_key_level=key_level.key_level_id,
                state="TRIGGERED",
                candle_refs=tuple(c.timestamp_close.isoformat() for c in m15[breakout_index : trigger_index + 1]),
                controlling_extreme=None,
                signal_status="SIGNAL_GENERATED",
                invalidation_reason=None,
            ),
        )

    @staticmethod
    def _completed_m15(candles: Sequence[MarketCandle]) -> tuple[MarketCandle, ...]:
        return tuple(
            sorted(
                (c for c in candles if c.timeframe is Timeframe.M15),
                key=lambda c: c.timestamp_close,
            )
        )

    @staticmethod
    def _h1_direction(structure: MarketStructureState) -> Direction | None:
        if structure.regime is Regime.UPTREND:
            return Direction.BUY
        if structure.regime is Regime.DOWNTREND:
            return Direction.SELL
        return None

    @staticmethod
    def _confirmed_swings(candles: Sequence[MarketCandle]) -> tuple[_M15Swing, ...]:
        swings: list[_M15Swing] = []
        for i in range(1, len(candles) - 1):
            prev_candle, middle, next_candle = candles[i - 1], candles[i], candles[i + 1]
            if middle.high > prev_candle.high and middle.high > next_candle.high:
                swings.append(_M15Swing(middle, SwingKind.HIGH))
            if middle.low < prev_candle.low and middle.low < next_candle.low:
                swings.append(_M15Swing(middle, SwingKind.LOW))
        return tuple(swings)

    @staticmethod
    def _most_recent_opposing_swing(
        swings: Sequence[_M15Swing], direction: Direction
    ) -> _M15Swing | None:
        wanted = SwingKind.HIGH if direction is Direction.BUY else SwingKind.LOW
        candidates = [s for s in swings if s.kind is wanted]
        return max(candidates, key=lambda s: s.candle.timestamp_close, default=None)

    @staticmethod
    def _find_breakout(
        candles: Sequence[MarketCandle], swing: _M15Swing, direction: Direction
    ) -> int | None:
        start = next((i for i, c in enumerate(candles) if c is swing.candle), None)
        if start is None:
            return None
        level = swing.candle.high if direction is Direction.BUY else swing.candle.low
        for i in range(start + 2, len(candles)):
            if (candles[i].close > level) if direction is Direction.BUY else (candles[i].close < level):
                return i
        return None

    @staticmethod
    def _find_retest(
        candles: Sequence[MarketCandle], breakout_index: int, level: Decimal, direction: Direction
    ) -> int | None:
        for i in range(breakout_index + 1, len(candles)):
            candle = candles[i]
            touches = candle.low <= level <= candle.high
            if touches:
                return i
        return None

    @staticmethod
    def _is_rejection(candle: MarketCandle, direction: Direction) -> bool:
        body = abs(candle.close - candle.open)
        if direction is Direction.BUY:
            lower_wick = min(candle.open, candle.close) - candle.low
            return lower_wick > body and candle.close > candle.open and candle.close >= candle.low + (candle.high - candle.low) * Decimal("0.6666666666666666666666666667")
        upper_wick = candle.high - max(candle.open, candle.close)
        return upper_wick > body and candle.close < candle.open and candle.close <= candle.high - (candle.high - candle.low) * Decimal("0.6666666666666666666666666667")

    @staticmethod
    def _structure_aligns(
        candles: Sequence[MarketCandle], rejection_index: int, direction: Direction
    ) -> bool:
        if rejection_index < 2:
            return False
        prior = candles[rejection_index - 1]
        before = candles[rejection_index - 2]
        current = candles[rejection_index]
        if direction is Direction.BUY:
            return current.high > prior.high or current.low > before.low
        return current.low < prior.low or current.high < before.high

    @staticmethod
    def _select_key_level_for_reference(key_levels: Sequence[KeyLevel]) -> KeyLevel:
        # Selection is intentionally not a strategy rule. The confirmation port
        # currently receives detected levels only; deterministic selection must
        # be supplied by the downstream governing-key-level component.
        if len(key_levels) != 1:
            raise ValueError("MS-0.3 requires one downstream-selected setup_key_level")
        return key_levels[0]

    @classmethod
    def _pending_cp1(
        cls, direction: Direction, key_levels: Sequence[KeyLevel], breakout_index: int, retest_index: int
    ) -> ConfirmationSequence:
        key_level = cls._select_key_level_for_reference(key_levels)
        return ConfirmationSequence(
            setup_id=cls._setup_id(direction, key_level, None),
            confirmation_type=ConfirmationType.CP1,
            direction=direction,
            setup_key_level=key_level.key_level_id,
            state="PENDING",
            candle_refs=(str(breakout_index), str(retest_index)),
            controlling_extreme=None,
            signal_status="PENDING",
            invalidation_reason=None,
        )

    @staticmethod
    def _setup_id(direction: Direction, key_level: KeyLevel, trigger: MarketCandle | None) -> str:
        payload = f"{CONFIRMATION_VERSION}|{direction.value}|{key_level.key_level_id}|{trigger.timestamp_close.isoformat() if trigger else 'PENDING'}"
        return f"CP1-{sha256(payload.encode('utf-8')).hexdigest()[:16]}"


__all__ = ["CONFIRMATION_VERSION", "M15ConfirmationEngine"]
