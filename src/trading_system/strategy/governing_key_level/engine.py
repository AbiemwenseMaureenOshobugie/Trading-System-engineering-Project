"""Deterministic governing Key-Level selection."""

from __future__ import annotations

from trading_system.application.ports import GoverningKeyLevelPort
from trading_system.domain import (
    Direction,
    GoverningKeyLevelRequest,
    GoverningKeyLevelResult,
    GoverningKeyLevelStatus,
    KeyLevel,
    SwingKind,
)

GOVERNING_KEY_LEVEL_VERSION = "GKS-0.1"


class GoverningKeyLevelEngine(GoverningKeyLevelPort):
    """Select exactly one structurally associated, direction-compatible Key Level."""

    def select(self, request: GoverningKeyLevelRequest) -> GoverningKeyLevelResult:
        evidence_ref = self._controlling_level_evidence_ref(request)
        compatible = tuple(
            level
            for level in request.key_levels
            if level.active
            and self._role_is_compatible(level, request.direction)
            and evidence_ref in level.evidence_refs
        )
        ids = tuple(level.key_level_id for level in compatible)

        if len(compatible) == 1:
            return GoverningKeyLevelResult(
                direction=request.direction,
                controlling_level_evidence_ref=evidence_ref,
                selected_key_level=compatible[0],
                eligible_key_level_ids=ids,
                status=GoverningKeyLevelStatus.SELECTED,
                reason_codes=("GOVERNING_KEY_LEVEL_SELECTED",),
            )

        if len(compatible) == 0:
            return GoverningKeyLevelResult(
                direction=request.direction,
                controlling_level_evidence_ref=evidence_ref,
                selected_key_level=None,
                eligible_key_level_ids=(),
                status=GoverningKeyLevelStatus.NO_GOVERNING_KEY_LEVEL,
                reason_codes=("NO_GOVERNING_KEY_LEVEL",),
            )

        return GoverningKeyLevelResult(
            direction=request.direction,
            controlling_level_evidence_ref=evidence_ref,
            selected_key_level=None,
            eligible_key_level_ids=ids,
            status=GoverningKeyLevelStatus.STRUCTURAL_CONSISTENCY_FAILURE,
            reason_codes=("MULTIPLE_GOVERNING_KEY_LEVELS",),
        )

    @staticmethod
    def _controlling_level_evidence_ref(request: GoverningKeyLevelRequest) -> str | None:
        controlling = request.structure.controlling_level
        if controlling is None:
            return None
        return f"SWING:{controlling.kind.value}:{controlling.timestamp.isoformat()}"

    @staticmethod
    def _role_is_compatible(level: KeyLevel, direction: Direction) -> bool:
        required_role = "SUPPORT" if direction is Direction.BUY else "RESISTANCE"
        return level.role == required_role


__all__ = ["GOVERNING_KEY_LEVEL_VERSION", "GoverningKeyLevelEngine"]
