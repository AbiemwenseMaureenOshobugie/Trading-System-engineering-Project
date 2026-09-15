"""Deterministic MS-0.1A H1 market-structure engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from trading_system.application.ports import H1MarketStructurePort
from trading_system.domain import (
    MarketCandle,
    MarketStructureState,
    PriceZone,
    Regime,
    SwingKind,
    SwingPoint,
    Timeframe,
)

STRUCTURE_VERSION = "MS-0.1A"


@dataclass(frozen=True, slots=True)
class _Candidate:
    index: int
    kind: SwingKind
    candle: MarketCandle

    @property
    def extreme(self) -> Decimal:
        return self.candle.high if self.kind is SwingKind.HIGH else self.candle.low

    @property
    def zone(self) -> PriceZone:
        if self.kind is SwingKind.HIGH:
            return PriceZone(self.candle.high, max(self.candle.open, self.candle.close))
        return PriceZone(min(self.candle.open, self.candle.close), self.candle.low)

    @property
    def swing(self) -> SwingPoint:
        return SwingPoint(self.candle.timestamp_open, self.extreme, self.kind)


@dataclass(frozen=True, slots=True)
class _Confirmed:
    candidate: _Candidate
    confirmed_at: datetime

    @property
    def swing(self) -> SwingPoint:
        return self.candidate.swing

    @property
    def zone(self) -> PriceZone:
        return self.candidate.zone


class H1MarketStructureEngine(H1MarketStructurePort):
    """Evaluate the frozen MS-0.1A contract without AI/ML or side effects."""

    def evaluate(
        self,
        *,
        candles: Sequence[MarketCandle],
        evaluation_cutoff: datetime,
    ) -> MarketStructureState:
        if evaluation_cutoff.tzinfo is None:
            raise ValueError("evaluation_cutoff must be timezone-aware")

        eligible = self._eligible_candles(candles, evaluation_cutoff)
        events: list[str] = []
        if not eligible:
            return self._state(
                Regime.UNCLEAR, (), (), None, None, None,
                ("INITIAL_UNCLEAR_INSUFFICIENT_HISTORY",), evaluation_cutoff,
            )

        candidates = self._candidates(eligible, events)
        confirmed = self._confirm_candidates(eligible, candidates, events)
        meaningful = self._meaningful_swings(confirmed, events)
        labels = self._relationship_labels(meaningful)
        regime, controlling, upper, lower = self._classify(
            eligible, meaningful, labels, events
        )

        highs = tuple(x.swing for x in meaningful if x.swing.kind is SwingKind.HIGH)
        lows = tuple(x.swing for x in meaningful if x.swing.kind is SwingKind.LOW)
        return self._state(
            regime, highs, lows, controlling, upper, lower, events, evaluation_cutoff
        )

    @staticmethod
    def _eligible_candles(
        candles: Sequence[MarketCandle], cutoff: datetime
    ) -> list[MarketCandle]:
        eligible = [
            c for c in candles
            if c.timeframe is Timeframe.H1 and c.timestamp_close <= cutoff
        ]
        return sorted(eligible, key=lambda c: c.timestamp_open)

    @staticmethod
    def _candidates(
        candles: Sequence[MarketCandle], events: list[str]
    ) -> list[_Candidate]:
        result: list[_Candidate] = []
        for i in range(1, len(candles) - 1):
            left, middle, right = candles[i - 1], candles[i], candles[i + 1]
            high = middle.high > left.high and middle.high > right.high
            low = middle.low < left.low and middle.low < right.low
            if high and low:
                events.append(f"DUAL_CANDIDATE_REJECTED:{middle.timestamp_open.isoformat()}")
            elif high:
                result.append(_Candidate(i, SwingKind.HIGH, middle))
            elif low:
                result.append(_Candidate(i, SwingKind.LOW, middle))
        return result

    @staticmethod
    def _confirm_candidates(
        candles: Sequence[MarketCandle],
        candidates: Sequence[_Candidate],
        events: list[str],
    ) -> list[_Confirmed]:
        """Replay the single active candidate/opposing-swing lifecycle."""
        confirmed: list[_Confirmed] = []
        active: _Candidate | None = None
        opposing: _Candidate | None = None
        by_index = {candidate.index: candidate for candidate in candidates}

        for i, candle in enumerate(candles):
            candidate = by_index.get(i - 1)
            if candidate is not None:
                if active is None:
                    active, opposing = candidate, None
                elif opposing is None:
                    if candidate.kind is active.kind:
                        active = candidate
                        events.append(f"CANDIDATE_REPLACED:{candidate.candle.timestamp_open.isoformat()}")
                    else:
                        opposing = candidate
                        events.append(f"OPPOSING_SWING_FORMED:{candidate.candle.timestamp_open.isoformat()}")
                elif candidate.kind is opposing.kind:
                    replaces = (
                        candidate.kind is SwingKind.LOW and candidate.extreme < opposing.extreme
                    ) or (
                        candidate.kind is SwingKind.HIGH and candidate.extreme > opposing.extreme
                    )
                    if replaces:
                        opposing = candidate
                        events.append(f"OPPOSING_SWING_UPDATED:{candidate.candle.timestamp_open.isoformat()}")

            if active is None or opposing is None:
                continue
            broken = (
                active.kind is SwingKind.HIGH and candle.close < opposing.extreme
            ) or (
                active.kind is SwingKind.LOW and candle.close > opposing.extreme
            )
            if broken:
                confirmed.append(_Confirmed(active, candle.timestamp_close))
                events.append(f"SWING_CONFIRMED:{active.candle.timestamp_open.isoformat()}")
                active = opposing = None

        return confirmed

    @staticmethod
    def _meaningful_swings(
        confirmed: Sequence[_Confirmed], events: list[str]
    ) -> list[_Confirmed]:
        """Apply Phase 1 references, then active-chain structural participation."""
        meaningful: list[_Confirmed] = []
        first_high = False
        first_low = False
        for item in sorted(confirmed, key=lambda x: x.swing.timestamp):
            if item.swing.kind is SwingKind.HIGH:
                if not first_high:
                    first_high = True
                    meaningful.append(item)
                    events.append(f"SWING_MEANINGFUL_PHASE1:{item.swing.timestamp.isoformat()}")
                else:
                    meaningful.append(item)
                    events.append(f"SWING_MEANINGFUL:{item.swing.timestamp.isoformat()}")
            else:
                if not first_low:
                    first_low = True
                    meaningful.append(item)
                    events.append(f"SWING_MEANINGFUL_PHASE1:{item.swing.timestamp.isoformat()}")
                else:
                    meaningful.append(item)
                    events.append(f"SWING_MEANINGFUL:{item.swing.timestamp.isoformat()}")
        return meaningful

    @staticmethod
    def _overlap(a: PriceZone, b: PriceZone) -> bool:
        return a.lower <= b.upper and b.lower <= a.upper

    def _relationship_labels(self, meaningful: Sequence[_Confirmed]) -> dict[datetime, str]:
        labels: dict[datetime, str] = {}
        prior_high: _Confirmed | None = None
        prior_low: _Confirmed | None = None
        for item in sorted(meaningful, key=lambda x: x.swing.timestamp):
            if item.swing.kind is SwingKind.HIGH:
                if prior_high is not None:
                    labels[item.swing.timestamp] = (
                        "EQ_HIGH" if self._overlap(item.zone, prior_high.zone)
                        else "HH" if item.swing.price > prior_high.swing.price
                        else "LH"
                    )
                prior_high = item
            else:
                if prior_low is not None:
                    labels[item.swing.timestamp] = (
                        "EQ_LOW" if self._overlap(item.zone, prior_low.zone)
                        else "HL" if item.swing.price > prior_low.swing.price
                        else "LL"
                    )
                prior_low = item
        return labels

    def _classify(
        self,
        eligible: Sequence[MarketCandle],
        meaningful: Sequence[_Confirmed],
        labels: dict[datetime, str],
        events: list[str],
    ) -> tuple[Regime, SwingPoint | None, PriceZone | None, PriceZone | None]:
        highs = [x for x in meaningful if x.swing.kind is SwingKind.HIGH]
        lows = [x for x in meaningful if x.swing.kind is SwingKind.LOW]
        upper, lower = self._bounding_pair(highs, lows)

        if upper is not None and lower is not None:
            upper_reactions, lower_reactions = self._range_reactions(meaningful, upper, lower)
            if self._alternates(upper_reactions, lower_reactions):
                events.extend(("RANGE_BOUNDARIES_SELECTED", "RANGE_ALTERNATING_REACTIONS_CONFIRMED"))
                breakout = self._range_breakout(eligible, meaningful, upper, lower)
                if breakout is not None:
                    events.append(f"RANGE_BREAKOUT_{breakout}")
                    return Regime.TRANSITION, None, upper, lower
                if not self._has_established_trend(labels):
                    return Regime.RANGE, None, upper, lower

        up, up_control = self._trend_status("UP", meaningful, labels)
        if up:
            if self._invalidated(eligible, up_control):
                events.append("UPTREND_INVALIDATED")
                return Regime.TRANSITION, up_control, upper, lower
            events.append("UPTREND_ESTABLISHED")
            return Regime.UPTREND, up_control, upper, lower

        down, down_control = self._trend_status("DOWN", meaningful, labels)
        if down:
            if self._invalidated(eligible, down_control):
                events.append("DOWNTREND_INVALIDATED")
                return Regime.TRANSITION, down_control, upper, lower
            events.append("DOWNTREND_ESTABLISHED")
            return Regime.DOWNTREND, down_control, upper, lower

        return Regime.UNCLEAR, None, upper, lower

    @staticmethod
    def _trend_status(
        direction: str,
        meaningful: Sequence[_Confirmed],
        labels: dict[datetime, str],
    ) -> tuple[bool, SwingPoint | None]:
        first, second = ("HH", "HL") if direction == "UP" else ("LH", "LL")
        firsts = [x for x in meaningful if labels.get(x.swing.timestamp) == first]
        seconds = [x for x in meaningful if labels.get(x.swing.timestamp) == second]
        if len(firsts) < 2 or len(seconds) < 2:
            return False, None
        controlling = seconds[-1] if direction == "UP" else firsts[-1]
        return True, controlling.swing

    @staticmethod
    def _invalidated(candles: Sequence[MarketCandle], controlling: SwingPoint | None) -> bool:
        if controlling is None:
            return False
        for candle in candles:
            if candle.timestamp_close <= controlling.timestamp:
                continue
            if controlling.kind is SwingKind.LOW and candle.close < controlling.price:
                return True
            if controlling.kind is SwingKind.HIGH and candle.close > controlling.price:
                return True
        return False

    @staticmethod
    def _has_established_trend(labels: dict[datetime, str]) -> bool:
        return (
            sum(v == "HH" for v in labels.values()) >= 2
            and sum(v == "HL" for v in labels.values()) >= 2
        ) or (
            sum(v == "LH" for v in labels.values()) >= 2
            and sum(v == "LL" for v in labels.values()) >= 2
        )

    @staticmethod
    def _bounding_pair(
        highs: Sequence[_Confirmed], lows: Sequence[_Confirmed]
    ) -> tuple[PriceZone | None, PriceZone | None]:
        if not highs or not lows:
            return None, None
        upper = max(highs, key=lambda x: (x.zone.upper, x.zone.lower, x.swing.timestamp)).zone
        lower = min(lows, key=lambda x: (x.zone.lower, x.zone.upper, x.swing.timestamp)).zone
        return upper, lower

    def _range_reactions(
        self,
        meaningful: Sequence[_Confirmed],
        upper: PriceZone,
        lower: PriceZone,
    ) -> tuple[list[datetime], list[datetime]]:
        upper_reactions: list[datetime] = []
        lower_reactions: list[datetime] = []
        for item in sorted(meaningful, key=lambda x: x.swing.timestamp):
            if item.swing.kind is SwingKind.HIGH and self._overlap(item.zone, upper):
                upper_reactions.append(item.swing.timestamp)
            elif item.swing.kind is SwingKind.LOW and self._overlap(item.zone, lower):
                lower_reactions.append(item.swing.timestamp)
        return upper_reactions, lower_reactions

    @staticmethod
    def _alternates(upper: Sequence[datetime], lower: Sequence[datetime]) -> bool:
        sequence = sorted(
            [(t, "U") for t in upper] + [(t, "L") for t in lower],
            key=lambda x: x[0],
        )
        if len(sequence) < 2:
            return False
        previous = sequence[0][1]
        switches = 0
        for _, side in sequence[1:]:
            if side != previous:
                switches += 1
                previous = side
        return switches >= 1

    @staticmethod
    def _range_breakout(
        candles: Sequence[MarketCandle],
        meaningful: Sequence[_Confirmed],
        upper: PriceZone,
        lower: PriceZone,
    ) -> str | None:
        reactions = [
            item.swing.timestamp
            for item in meaningful
            if (
                item.swing.kind is SwingKind.HIGH
                and H1MarketStructureEngine._overlap(item.zone, upper)
            ) or (
                item.swing.kind is SwingKind.LOW
                and H1MarketStructureEngine._overlap(item.zone, lower)
            )
        ]
        if not reactions:
            return None
        start = max(reactions)
        for candle in candles:
            if candle.timestamp_close <= start:
                continue
            if candle.close > upper.upper:
                return "UP"
            if candle.close < lower.lower:
                return "DOWN"
        return None

    @staticmethod
    def _state(
        regime: Regime,
        highs: tuple[SwingPoint, ...],
        lows: tuple[SwingPoint, ...],
        controlling: SwingPoint | None,
        upper: PriceZone | None,
        lower: PriceZone | None,
        events: Sequence[str],
        evaluated_at: datetime,
    ) -> MarketStructureState:
        return MarketStructureState(
            regime=regime,
            structure_version=STRUCTURE_VERSION,
            meaningful_highs=highs,
            meaningful_lows=lows,
            controlling_level=controlling,
            range_upper_boundary=upper,
            range_lower_boundary=lower,
            structural_events=tuple(events),
            evaluated_at=evaluated_at,
        )


__all__ = ["H1MarketStructureEngine", "STRUCTURE_VERSION"]
