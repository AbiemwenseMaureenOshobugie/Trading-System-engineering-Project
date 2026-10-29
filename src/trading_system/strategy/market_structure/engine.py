"""Deterministic MS-0.1A H1 market-structure engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Sequence

from trading_system.application.ports import H1MarketStructurePort
from trading_system.domain import (
    ClassificationRecord,
    MarketCandle,
    MarketStructureState,
    PriceZone,
    Regime,
    SwingClassification,
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
            return PriceZone(max(self.candle.open, self.candle.close), self.candle.high)
        return PriceZone(self.candle.low, min(self.candle.open, self.candle.close))

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

@dataclass(frozen=True, slots=True)
class _AdmissionLedger:
    """Internal immutable ledger of admission outcomes per evaluation.

    Round 1: unresolved and excluded are always empty. Round 2 populates them
    when the admission gate is enforced. classification is a tuple ordered
    by swing_timestamp (immutable, per Amendment 02).
    """

    admitted: tuple[_Confirmed, ...]
    unresolved: tuple[_Confirmed, ...]
    excluded: tuple[_Confirmed, ...]
    classification: tuple[ClassificationRecord, ...]
    episode_start: datetime | None


@dataclass(frozen=True, slots=True)
class _AdmissionResult:
    """Internal return value of _meaningful_swings."""

    ledger: _AdmissionLedger
    events: tuple[str, ...]

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
        admission = self._meaningful_swings(confirmed)
        events.extend(admission.events)
        meaningful = list(admission.ledger.admitted)
        labels = self._relationship_labels(meaningful)
        regime, controlling, upper, lower = self._classify(
            eligible, meaningful, labels, events
        )

        highs = tuple(x.swing for x in meaningful if x.swing.kind is SwingKind.HIGH)
        lows = tuple(x.swing for x in meaningful if x.swing.kind is SwingKind.LOW)
        confirmed_swings = tuple(x.swing for x in confirmed)
        return self._state(
            regime, highs, lows, controlling, upper, lower, events, evaluation_cutoff,
            classification_records=admission.ledger.classification,
            confirmed_swings=confirmed_swings,
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
                        old_ts = opposing.candle.timestamp_open.isoformat()
                        new_ts = candidate.candle.timestamp_open.isoformat()
                        opposing = candidate
                        events.append(f"OPPOSING_SWING_UPDATED:{old_ts}:{new_ts}")

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

    def _meaningful_swings(
        self,
        confirmed: Sequence[_Confirmed],
    ) -> _AdmissionResult:
        """Apply Phase 1 bootstrap and classification recording.

        Round 1: implements Phase 1 bootstrap (per Amendment 05 section A) and
        records classification + reference for each confirmed swing.
        Admission gate enforcement (unresolved/excluded states) is Round 2.

        Episode start is always None in Round 1 (single-episode assumption).
        Round 2 extends this to derive episode start from prior invalidations.
        """
        admitted: list[_Confirmed] = []
        classification_records: list[ClassificationRecord] = []
        local_events: list[str] = []

        prior_admitted_high: _Confirmed | None = None
        prior_admitted_low: _Confirmed | None = None

        for item in sorted(confirmed, key=lambda x: x.swing.timestamp):
            ts = item.swing.timestamp
            if item.swing.kind is SwingKind.HIGH:
                if prior_admitted_high is None:
                    admitted.append(item)
                    classification_records.append(
                        ClassificationRecord(
                            swing_timestamp=ts,
                            swing_kind=SwingKind.HIGH,
                            swing_price=item.swing.price,
                            classification=None,
                            reference_timestamp=None,
                            is_bootstrap=True,
                        )
                    )
                    local_events.append(
                        f"SWING_MEANINGFUL_PHASE1:{ts.isoformat()}"
                    )
                    local_events.append(
                        f"SWING_CONFIRMED_UNRESOLVED:{ts.isoformat()}:bootstrap"
                    )
                else:
                    if self._overlap(item.zone, prior_admitted_high.zone):
                        label = SwingClassification.EQ_HIGH
                    elif item.swing.price > prior_admitted_high.swing.price:
                        label = SwingClassification.HH
                    else:
                        label = SwingClassification.LH
                    classification_records.append(
                        ClassificationRecord(
                            swing_timestamp=ts,
                            swing_kind=SwingKind.HIGH,
                            swing_price=item.swing.price,
                            classification=label,
                            reference_timestamp=prior_admitted_high.swing.timestamp,
                            is_bootstrap=False,
                        )
                    )
                    admitted.append(item)
                    local_events.append(f"SWING_MEANINGFUL:{ts.isoformat()}")
                prior_admitted_high = item
            else:
                if prior_admitted_low is None:
                    admitted.append(item)
                    classification_records.append(
                        ClassificationRecord(
                            swing_timestamp=ts,
                            swing_kind=SwingKind.LOW,
                            swing_price=item.swing.price,
                            classification=None,
                            reference_timestamp=None,
                            is_bootstrap=True,
                        )
                    )
                    local_events.append(
                        f"SWING_MEANINGFUL_PHASE1:{ts.isoformat()}"
                    )
                    local_events.append(
                        f"SWING_CONFIRMED_UNRESOLVED:{ts.isoformat()}:bootstrap"
                    )
                else:
                    if self._overlap(item.zone, prior_admitted_low.zone):
                        label = SwingClassification.EQ_LOW
                    elif item.swing.price > prior_admitted_low.swing.price:
                        label = SwingClassification.HL
                    else:
                        label = SwingClassification.LL
                    classification_records.append(
                        ClassificationRecord(
                            swing_timestamp=ts,
                            swing_kind=SwingKind.LOW,
                            swing_price=item.swing.price,
                            classification=label,
                            reference_timestamp=prior_admitted_low.swing.timestamp,
                            is_bootstrap=False,
                        )
                    )
                    admitted.append(item)
                    local_events.append(f"SWING_MEANINGFUL:{ts.isoformat()}")
                prior_admitted_low = item

        ledger = _AdmissionLedger(
            admitted=tuple(admitted),
            unresolved=(),
            excluded=(),
            classification=tuple(classification_records),
            episode_start=None,
        )
        return _AdmissionResult(ledger=ledger, events=tuple(local_events))

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
                breakout = (
                    None
                    if self._has_established_trend(labels)
                    else self._range_breakout(eligible, meaningful, upper, lower)
                )
                if breakout is not None:
                    events.append(f"RANGE_BREAKOUT_{breakout}")
                    return Regime.TRANSITION, None, upper, lower
                if not self._has_established_trend(labels):
                    return Regime.RANGE, None, upper, lower

        up, up_control = self._trend_status("UP", meaningful, labels)
        if up:
            invalidation_ts = self._first_invalidation_timestamp(eligible, up_control)
            if invalidation_ts is not None:
                events.append("UPTREND_INVALIDATED")
                episode_meaningful = [
                    x for x in meaningful if x.swing.timestamp >= invalidation_ts
                ]
                episode_labels = self._relationship_labels(episode_meaningful)
                down2, down_control2 = self._trend_status("DOWN", episode_meaningful, episode_labels)
                if down2 and self._first_invalidation_timestamp(eligible, down_control2) is None:
                    events.append("DOWNTREND_ESTABLISHED")
                    return Regime.DOWNTREND, down_control2, upper, lower
                return Regime.TRANSITION, None, upper, lower
            events.append("UPTREND_ESTABLISHED")
            return Regime.UPTREND, up_control, upper, lower

        down, down_control = self._trend_status("DOWN", meaningful, labels)
        if down:
            invalidation_ts = self._first_invalidation_timestamp(eligible, down_control)
            if invalidation_ts is not None:
                events.append("DOWNTREND_INVALIDATED")
                episode_meaningful = [
                    x for x in meaningful if x.swing.timestamp >= invalidation_ts
                ]
                episode_labels = self._relationship_labels(episode_meaningful)
                up2, up_control2 = self._trend_status("UP", episode_meaningful, episode_labels)
                if up2 and self._first_invalidation_timestamp(eligible, up_control2) is None:
                    events.append("UPTREND_ESTABLISHED")
                    return Regime.UPTREND, up_control2, upper, lower
                return Regime.TRANSITION, None, upper, lower
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
    def _first_invalidation_timestamp(
        candles: Sequence[MarketCandle], controlling: SwingPoint | None
    ) -> datetime | None:
        if controlling is None:
            return None
        for candle in candles:
            if candle.timestamp_close <= controlling.timestamp:
                continue
            if controlling.kind is SwingKind.LOW and candle.close < controlling.price:
                return candle.timestamp_close
            if controlling.kind is SwingKind.HIGH and candle.close > controlling.price:
                return candle.timestamp_close
        return None

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
        later = [candle for candle in candles if candle.timestamp_close > start]
        for index, candle in enumerate(later):
            if candle.close >= upper.upper:
                direction = "UP"
            elif candle.close <= lower.lower:
                direction = "DOWN"
            else:
                continue
            if index + 1 == len(later):
                return None
            follow_close = later[index + 1].close
            if direction == "UP" and follow_close >= upper.upper:
                return "UP"
            if direction == "DOWN" and follow_close <= lower.lower:
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
        classification_records: tuple[ClassificationRecord, ...] = (),
        confirmed_swings: tuple[SwingPoint, ...] = (),
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
            classification_records=classification_records,
            confirmed_swings=confirmed_swings,
        )


__all__ = ["H1MarketStructureEngine", "STRUCTURE_VERSION"]
