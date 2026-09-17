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
    SwingKind,
    SwingPoint,
    Timeframe,
)

CONFIRMATION_VERSION = "MS-0.3"


@dataclass(frozen=True, slots=True)
class ConfirmedM15Swing:
    swing: SwingPoint
    confirmed_at: datetime
    candle: MarketCandle


class M15SwingDetector:
    """Implement corrected M15-06 three-candle swing confirmation."""

    def confirm(self, *, candles: Sequence[MarketCandle]) -> Sequence[ConfirmedM15Swing]:
        eligible = _m15_candles(candles)
        confirmed: list[ConfirmedM15Swing] = []
        for index in range(1, len(eligible) - 1):
            left, middle, right = eligible[index - 1 : index + 2]
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
            if is_high == is_low:
                continue
            kind = SwingKind.HIGH if is_high else SwingKind.LOW
            extreme = middle.high if is_high else middle.low
            confirmed.append(
                ConfirmedM15Swing(
                    swing=SwingPoint(middle.timestamp_open, extreme, kind),
                    confirmed_at=right.timestamp_close,
                    candle=middle,
                )
            )
        return tuple(confirmed)


class M15ConfirmationEngine(ConfirmationEnginePort):
    """Evaluate CP-1 and CP-2 against one selected governing Key Level."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
        setup_key_level: KeyLevel,
    ) -> Sequence[ConfirmationSequence]:
        if not setup_key_level.active:
            return ()
        ordered = _m15_candles(candles)
        if not ordered:
            return ()
        direction = self._h1_direction(structure)
        if direction is None:
            return ()
        h1_invalidated_at = self._h1_invalidation_time(candles, structure)
        swings = M15SwingDetector().confirm(candles=ordered)
        results: list[ConfirmationSequence] = []
        cp1 = self._evaluate_cp1(ordered, direction, setup_key_level, swings, h1_invalidated_at)
        if cp1 is not None:
            results.append(cp1)
        results.extend(self._evaluate_cp2(ordered, direction, setup_key_level, h1_invalidated_at))
        return tuple(results)

    @staticmethod
    def _h1_direction(structure: MarketStructureState) -> Direction | None:
        if structure.regime.value == "UPTREND":
            return Direction.BUY
        if structure.regime.value == "DOWNTREND":
            return Direction.SELL
        return None

    @staticmethod
    def _h1_invalidation_time(
        candles: Sequence[MarketCandle], structure: MarketStructureState
    ) -> datetime | None:
        controlling = structure.controlling_level
        if controlling is None:
            return None
        for candle in sorted((c for c in candles if c.timeframe is Timeframe.H1), key=lambda c: c.timestamp_close):
            if candle.timestamp_close <= controlling.timestamp:
                continue
            if structure.regime.value == "UPTREND" and candle.close < controlling.price:
                return candle.timestamp_close
            if structure.regime.value == "DOWNTREND" and candle.close > controlling.price:
                return candle.timestamp_close
        return None

    def _evaluate_cp1(
        self,
        candles: Sequence[MarketCandle],
        direction: Direction,
        key_level: KeyLevel,
        swings: Sequence[ConfirmedM15Swing],
        h1_invalidated_at: datetime | None,
    ) -> ConfirmationSequence | None:
        breakout: tuple[int, ConfirmedM15Swing] | None = None
        reference_kind = SwingKind.HIGH if direction is Direction.BUY else SwingKind.LOW
        for i, candle in enumerate(candles):
            prior = [s for s in swings if s.confirmed_at <= candle.timestamp_close]
            candidates = [s for s in prior if s.swing.kind is reference_kind]
            if not candidates:
                continue
            reference = candidates[-1]
            broken = candle.close > reference.swing.price if direction is Direction.BUY else candle.close < reference.swing.price
            if broken:
                breakout = (i, reference)
                break
        if breakout is None:
            return None

        breakout_index, reference = breakout
        rejection_index: int | None = None
        for i in range(breakout_index + 1, len(candles)):
            candle = candles[i]
            if h1_invalidated_at is not None and candle.timestamp_close >= h1_invalidated_at:
                return None
            if _touches_price(candle, reference.swing.price) and _qualifies_rejection(candle, direction):
                rejection_index = i
                break
        if rejection_index is None:
            return None

        rejection = candles[rejection_index]
        aligned = _m15_aligned_after_breakout(
            swings, direction, reference.confirmed_at, rejection.timestamp_close
        )
        refs = (_ref(candles[breakout_index]), _ref(rejection))
        if not aligned:
            return _sequence(
                ConfirmationType.CP1, direction, key_level, "PENDING_ALIGNMENT", refs,
                reference.swing.price, "PENDING", None
            )

        trigger_index = rejection_index + 1
        if trigger_index >= len(candles):
            return _sequence(
                ConfirmationType.CP1, direction, key_level, "PENDING_TRIGGER", refs,
                reference.swing.price, "PENDING", None
            )
        trigger = candles[trigger_index]
        refs = (*refs, _ref(trigger))
        if h1_invalidated_at is not None and h1_invalidated_at <= trigger.timestamp_close:
            return _sequence(
                ConfirmationType.CP1, direction, key_level, "INVALIDATED", refs,
                reference.swing.price, "SIGNAL_NONE", "H1_INVALIDATION_BEFORE_TRIGGER"
            )
        passed = trigger.close > rejection.high if direction is Direction.BUY else trigger.close < rejection.low
        if passed:
            return _sequence(
                ConfirmationType.CP1, direction, key_level, "TRIGGERED", refs,
                trigger.close, "SIGNAL_TRIGGERED", None
            )
        return _sequence(
            ConfirmationType.CP1, direction, key_level, "EXPIRED", refs,
            reference.swing.price, "SIGNAL_NONE", "CONFIRMATION_FAILED"
        )

    @staticmethod
    def _evaluate_cp2(
        candles: Sequence[MarketCandle],
        direction: Direction,
        key_level: KeyLevel,
        h1_invalidated_at: datetime | None,
    ) -> Sequence[ConfirmationSequence]:
        results: list[ConfirmationSequence] = []
        for index, c1 in enumerate(candles):
            if h1_invalidated_at is not None and c1.timestamp_close >= h1_invalidated_at:
                break
            if not _qualifies_rejection_at_key_level(c1, direction, key_level):
                continue
            sweep_extreme = _sweep_extreme(c1, direction, key_level)
            if index + 2 >= len(candles):
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "PENDING_RESPONSE",
                    (_ref(c1),), sweep_extreme, "PENDING", None
                ))
                continue
            c2, c3 = candles[index + 1], candles[index + 2]
            refs = (_ref(c1), _ref(c2), _ref(c3))
            if h1_invalidated_at is not None and h1_invalidated_at <= c3.timestamp_close:
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "INVALIDATED", refs,
                    sweep_extreme, "SIGNAL_NONE", "H1_INVALIDATION_BEFORE_ENTRY"
                ))
                continue
            if sweep_extreme is not None and _sweep_repenetrated(c2, c3, direction, sweep_extreme):
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "INVALIDATED", refs,
                    sweep_extreme, "SIGNAL_NONE", "SWEEP_REPENETRATION"
                ))
                continue
            if not _qualifies_cp2_c2(c1=c1, c2=c2, direction=direction):
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "EXPIRED", refs,
                    sweep_extreme, "SIGNAL_NONE", "CONFIRMATION_FAILED"
                ))
                continue
            if sweep_extreme is None:
                confirmed = _qualifies_cp2_ordinary_c3(c1=c1, c2=c2, c3=c3, direction=direction)
            elif direction is Direction.BUY:
                confirmed = c2.close > sweep_extreme and c2.close > c1.high and c3.close > c1.high and c3.close > c2.high
            else:
                confirmed = c2.close < sweep_extreme and c2.close < c1.low and c3.close < c1.low and c3.close < c2.low
            if confirmed:
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "TRIGGERED", refs,
                    sweep_extreme, "SIGNAL_TRIGGERED", None
                ))
            else:
                results.append(_sequence(
                    ConfirmationType.CP2, direction, key_level, "EXPIRED", refs,
                    sweep_extreme, "SIGNAL_NONE", "CONFIRMATION_FAILED"
                ))
        return tuple(results)


def _m15_aligned_after_breakout(
    swings: Sequence[ConfirmedM15Swing],
    direction: Direction,
    breakout_confirmation: datetime,
    rejection_close: datetime,
) -> bool:
    available = [s for s in swings if breakout_confirmation <= s.confirmed_at <= rejection_close]
    for kind in (SwingKind.HIGH, SwingKind.LOW):
        same = [s for s in available if s.swing.kind is kind]
        if len(same) < 2:
            continue
        previous, current = same[-2], same[-1]
        if direction is Direction.BUY and current.swing.price > previous.swing.price:
            return True
        if direction is Direction.SELL and current.swing.price < previous.swing.price:
            return True
    return False


def _qualifies_rejection_at_key_level(candle: MarketCandle, direction: Direction, key_level: KeyLevel) -> bool:
    return any(candle.low <= zone.upper and candle.high >= zone.lower for _, zone in key_level.source_zones) and _qualifies_rejection(candle, direction)


def _qualifies_rejection(candle: MarketCandle, direction: Direction) -> bool:
    body = abs(candle.close - candle.open)
    if body == 0:
        return False
    if direction is Direction.BUY:
        return candle.close > candle.open and candle.open - candle.low > body and candle.close >= candle.low + (candle.high - candle.low) * Decimal(2) / Decimal(3)
    return candle.close < candle.open and candle.high - candle.open > body and candle.close <= candle.high - (candle.high - candle.low) * Decimal(2) / Decimal(3)


def _sweep_extreme(candle: MarketCandle, direction: Direction, key_level: KeyLevel) -> Decimal | None:
    zones = [zone for _, zone in key_level.source_zones]
    if direction is Direction.BUY and any(candle.low < zone.lower for zone in zones):
        return candle.low
    if direction is Direction.SELL and any(candle.high > zone.upper for zone in zones):
        return candle.high
    return None


def _sweep_repenetrated(c2: MarketCandle, c3: MarketCandle, direction: Direction, sweep_extreme: Decimal) -> bool:
    if direction is Direction.BUY:
        return c2.low < sweep_extreme or c3.low < sweep_extreme
    return c2.high > sweep_extreme or c3.high > sweep_extreme


def _qualifies_cp2_c2(*, c1: MarketCandle, c2: MarketCandle, direction: Direction) -> bool:
    c1_body = abs(c1.close - c1.open)
    c2_body = abs(c2.close - c2.open)
    if direction is Direction.BUY:
        return c2.close > c2.open and c2_body > c1_body and c2.low >= c2.open
    return c2.close < c2.open and c2_body > c1_body and c2.high <= c2.open


def _qualifies_cp2_ordinary_c3(*, c1: MarketCandle, c2: MarketCandle, c3: MarketCandle, direction: Direction) -> bool:
    if direction is Direction.BUY:
        return c2.close > c1.high and c3.close > c1.high and c3.close > c2.high
    return c2.close < c1.low and c3.close < c1.low and c3.close < c2.low


def _m15_candles(candles: Sequence[MarketCandle]) -> list[MarketCandle]:
    return sorted((c for c in candles if c.timeframe is Timeframe.M15), key=lambda c: c.timestamp_open)


def _ref(candle: MarketCandle) -> str:
    return candle.timestamp_open.isoformat()


def _touches_price(candle: MarketCandle, price: Decimal) -> bool:
    return candle.low <= price <= candle.high


def _sequence(
    confirmation_type: ConfirmationType,
    direction: Direction,
    key_level: KeyLevel,
    state: str,
    candle_refs: tuple[str, ...],
    controlling_extreme: Decimal | None,
    signal_status: str,
    invalidation_reason: str | None,
) -> ConfirmationSequence:
    raw = "|".join((CONFIRMATION_VERSION, confirmation_type.value, direction.value, key_level.key_level_id, *candle_refs)).encode()
    return ConfirmationSequence(
        setup_id="CN-" + sha256(raw).hexdigest()[:16],
        confirmation_type=confirmation_type,
        direction=direction,
        setup_key_level=key_level.key_level_id,
        state=state,
        candle_refs=candle_refs,
        controlling_extreme=controlling_extreme,
        signal_status=signal_status,
        invalidation_reason=invalidation_reason,
    )


__all__ = ["CONFIRMATION_VERSION", "ConfirmedM15Swing", "M15ConfirmationEngine", "M15SwingDetector"]
