"""Deterministic MS-0.2 Key-Level detection engine."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from typing import Sequence

from trading_system.application.ports import KeyLevelEnginePort
from trading_system.domain import (
    KeyLevel,
    KeyLevelSource,
    MarketCandle,
    MarketStructureState,
    PriceZone,
    SwingKind,
)

KEY_LEVEL_VERSION = "MS-0.2"


@dataclass(frozen=True, slots=True)
class _SourceEvidence:
    source: KeyLevelSource
    zone: PriceZone
    evidence_ref: str
    state_history: tuple[str, ...]
    role: str | None = None


class KeyLevelDetectionEngine(KeyLevelEnginePort):
    """Convert approved structural evidence into deterministic Key Levels."""

    def detect(
        self,
        *,
        candles: Sequence[MarketCandle],
        structure: MarketStructureState,
    ) -> Sequence[KeyLevel]:
        evidence = self._collect_sources(candles, structure)
        groups = self._overlap_groups(evidence)
        return tuple(
            self._build_key_level(group, structure.evaluated_at) for group in groups
        )

    @staticmethod
    def _collect_sources(
        candles: Sequence[MarketCandle], structure: MarketStructureState
    ) -> list[_SourceEvidence]:
        evidence: list[_SourceEvidence] = []
        candles_by_open = {c.timestamp_open: c for c in candles}

        for swing in (*structure.meaningful_highs, *structure.meaningful_lows):
            candle = candles_by_open.get(swing.timestamp)
            if candle is None:
                raise ValueError(
                    f"missing source candle for meaningful swing at {swing.timestamp.isoformat()}"
                )
            if swing.kind is SwingKind.HIGH:
                zone = PriceZone(max(candle.open, candle.close), candle.high)
                role = "RESISTANCE"
            else:
                zone = PriceZone(min(candle.open, candle.close), candle.low)
                role = "SUPPORT"
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.VALIDATED_SWING,
                    zone,
                    f"SWING:{swing.kind.value}:{swing.timestamp.isoformat()}",
                    ("SOURCE_ESTABLISHED:MEANINGFUL_SWING",),
                    role,
                )
            )

        if structure.range_upper_boundary is not None:
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.RANGE_BOUNDARY,
                    structure.range_upper_boundary,
                    "RANGE_BOUNDARY:UPPER",
                    ("SOURCE_ESTABLISHED:RANGE_BOUNDARY",),
                    "RESISTANCE",
                )
            )

        if structure.range_lower_boundary is not None:
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.RANGE_BOUNDARY,
                    structure.range_lower_boundary,
                    "RANGE_BOUNDARY:LOWER",
                    ("SOURCE_ESTABLISHED:RANGE_BOUNDARY",),
                    "SUPPORT",
                )
            )

        events = set(structure.structural_events)
        if "RANGE_BREAKOUT_UP" in events and structure.range_upper_boundary is not None:
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.BREAKOUT_LEVEL,
                    structure.range_upper_boundary,
                    "BREAKOUT_LEVEL:UP:RANGE_UPPER",
                    ("SOURCE_ESTABLISHED:BREAKOUT_EVENT",),
                    "RESISTANCE",
                )
            )
        if "RANGE_BREAKOUT_DOWN" in events and structure.range_lower_boundary is not None:
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.BREAKOUT_LEVEL,
                    structure.range_lower_boundary,
                    "BREAKOUT_LEVEL:DOWN:RANGE_LOWER",
                    ("SOURCE_ESTABLISHED:BREAKOUT_EVENT",),
                    "SUPPORT",
                )
            )

        # Role reversal is provenance on an existing level, not a new zone.
        # Event format: ROLE_REVERSAL:<existing-source-evidence-ref>.
        source_by_ref = {item.evidence_ref: item for item in evidence}
        for event in sorted(events):
            prefix = "ROLE_REVERSAL:"
            if not event.startswith(prefix):
                continue
            source_ref = event[len(prefix) :]
            existing = source_by_ref.get(source_ref)
            if existing is None:
                continue
            evidence.append(
                _SourceEvidence(
                    KeyLevelSource.ROLE_REVERSAL,
                    existing.zone,
                    event,
                    ("SOURCE_ESTABLISHED:ROLE_REVERSAL",),
                    existing.role,
                )
            )

        return sorted(
            evidence,
            key=lambda item: (
                item.zone.lower,
                item.zone.upper,
                item.source.value,
                item.evidence_ref,
            ),
        )

    @staticmethod
    def _overlap(a: PriceZone, b: PriceZone) -> bool:
        return a.lower <= b.upper and b.lower <= a.upper

    @classmethod
    def _overlap_groups(
        cls, evidence: Sequence[_SourceEvidence]
    ) -> tuple[tuple[_SourceEvidence, ...], ...]:
        if not evidence:
            return ()

        remaining = set(range(len(evidence)))
        groups: list[tuple[_SourceEvidence, ...]] = []
        while remaining:
            seed = min(remaining)
            remaining.remove(seed)
            component = {seed}
            frontier = [seed]

            while frontier:
                current = frontier.pop()
                matches = {
                    index
                    for index in remaining
                    if cls._overlap(evidence[current].zone, evidence[index].zone)
                }
                remaining.difference_update(matches)
                component.update(matches)
                frontier.extend(sorted(matches))

            groups.append(
                tuple(
                    sorted(
                        (evidence[index] for index in component),
                        key=lambda item: (
                            item.source.value,
                            item.evidence_ref,
                            item.zone.lower,
                            item.zone.upper,
                        ),
                    )
                )
            )

        return tuple(
            sorted(
                groups,
                key=lambda group: (
                    group[0].zone.lower,
                    group[0].zone.upper,
                    group[0].source.value,
                    group[0].evidence_ref,
                ),
            )
        )

    @staticmethod
    def _build_key_level(
        group: Sequence[_SourceEvidence], evaluated_at: datetime
    ) -> KeyLevel:
        source_zones = tuple((item.source, item.zone) for item in group)
        source_types = tuple(dict.fromkeys(item.source for item in group))
        evidence_refs = tuple(item.evidence_ref for item in group)
        state_history = tuple(
            dict.fromkeys(
                history for item in group for history in item.state_history
            )
        )
        roles = tuple(dict.fromkeys(item.role for item in group if item.role))
        role = roles[0] if len(roles) == 1 else None
        return KeyLevel(
            key_level_id=KeyLevelDetectionEngine._identity(source_zones, evidence_refs),
            source_types=source_types,
            source_zones=source_zones,
            active=True,
            role=role,
            created_at=evaluated_at,
            updated_at=evaluated_at,
            evidence_refs=evidence_refs,
            state_history=state_history,
        )

    @staticmethod
    def _identity(
        source_zones: Sequence[tuple[KeyLevelSource, PriceZone]],
        evidence_refs: Sequence[str],
    ) -> str:
        payload = "|".join(
            [
                *(f"{source.value}:{zone.lower}:{zone.upper}" for source, zone in source_zones),
                *evidence_refs,
            ]
        )
        digest = sha256(payload.encode("utf-8")).hexdigest()[:16]
        return f"KL-{digest}"


__all__ = ["KEY_LEVEL_VERSION", "KeyLevelDetectionEngine"]
