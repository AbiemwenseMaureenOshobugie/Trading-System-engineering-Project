"""Deterministic MS-0.4 risk and trade-qualification engine."""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable

from trading_system.domain import (
    Direction,
    KeyLevel,
    RiskRequest,
    RiskResult,
    RiskStatus,
)

RISK_VERSION = "MS-0.4"
FIXED_RISK_RATE = Decimal("0.01")
MIN_RISK_REWARD = Decimal("2")


class RiskEngine:
    """Apply the locked MS-0.4 risk, stop, target, and sizing rules."""

    def assess(self, request: RiskRequest) -> RiskResult:
        candidate = request.candidate
        requested_risk = FIXED_RISK_RATE
        entry = candidate.signal_entry_price
        structural_sl = candidate.proposed_stop_loss

        if structural_sl is None:
            return self._rejected(
                candidate.decision_id,
                requested_risk,
                "MISSING_STRUCTURAL_STOP",
            )

        buffer = (
            request.spread
            + request.slippage
            + request.noise
            + request.volatility_adjustment
        )

        if candidate.direction is Direction.BUY:
            final_sl = structural_sl - buffer
            stop_distance = entry - final_sl
            if stop_distance <= 0:
                return self._rejected(
                    candidate.decision_id,
                    requested_risk,
                    "INVALID_STOP_DISTANCE",
                    structural_stop_loss=structural_sl,
                    final_stop_loss=final_sl,
                    stop_distance=stop_distance,
                )

            target = self._select_buy_target(request, entry, stop_distance)
            if target is None:
                return self._rejected(
                    candidate.decision_id,
                    requested_risk,
                    "TARGET_BELOW_MINIMUM_RR",
                    structural_stop_loss=structural_sl,
                    final_stop_loss=final_sl,
                    stop_distance=stop_distance,
                )
            target_distance = target - entry
        else:
            final_sl = structural_sl + buffer
            stop_distance = final_sl - entry
            if stop_distance <= 0:
                return self._rejected(
                    candidate.decision_id,
                    requested_risk,
                    "INVALID_STOP_DISTANCE",
                    structural_stop_loss=structural_sl,
                    final_stop_loss=final_sl,
                    stop_distance=stop_distance,
                )

            target = self._select_sell_target(request, entry, stop_distance)
            if target is None:
                return self._rejected(
                    candidate.decision_id,
                    requested_risk,
                    "TARGET_BELOW_MINIMUM_RR",
                    structural_stop_loss=structural_sl,
                    final_stop_loss=final_sl,
                    stop_distance=stop_distance,
                )
            target_distance = entry - target

        risk_reward = target_distance / stop_distance
        risk_amount = request.account_equity * requested_risk
        position_size = risk_amount / (
            stop_distance * request.value_per_price_unit
        )

        return RiskResult(
            decision_id=candidate.decision_id,
            requested_risk=requested_risk,
            approved_risk=requested_risk,
            position_size=position_size,
            entry_assumption=entry,
            structural_stop_loss=structural_sl,
            final_stop_loss=final_sl,
            target_price=target,
            stop_distance=stop_distance,
            target_distance=target_distance,
            risk_reward=risk_reward,
            risk_amount=risk_amount,
            status=RiskStatus.RISK_AUTHORIZED,
            reason_codes=("RISK_1_PERCENT",),
        )

    @staticmethod
    def _select_buy_target(
        request: RiskRequest, entry: Decimal, stop_distance: Decimal
    ) -> Decimal | None:
        boundaries = RiskEngine._opposing_boundaries(
            request.active_key_levels,
            request.setup_key_level_id,
            entry,
            Direction.BUY,
        )
        if not boundaries:
            return entry + (MIN_RISK_REWARD * stop_distance)

        target = min(boundaries, key=lambda price: price - entry)
        if (target - entry) / stop_distance < MIN_RISK_REWARD:
            return None
        return target

    @staticmethod
    def _select_sell_target(
        request: RiskRequest, entry: Decimal, stop_distance: Decimal
    ) -> Decimal | None:
        boundaries = RiskEngine._opposing_boundaries(
            request.active_key_levels,
            request.setup_key_level_id,
            entry,
            Direction.SELL,
        )
        if not boundaries:
            return entry - (MIN_RISK_REWARD * stop_distance)

        target = min(boundaries, key=lambda price: entry - price)
        if (entry - target) / stop_distance < MIN_RISK_REWARD:
            return None
        return target

    @staticmethod
    def _opposing_boundaries(
        key_levels: Iterable[KeyLevel],
        setup_key_level_id: str | None,
        entry: Decimal,
        direction: Direction,
    ) -> tuple[Decimal, ...]:
        boundaries: list[Decimal] = []

        for key_level in key_levels:
            if not key_level.active:
                continue
            if setup_key_level_id is not None and key_level.key_level_id == setup_key_level_id:
                continue

            for _, zone in key_level.source_zones:
                if direction is Direction.BUY:
                    if zone.lower > entry:
                        boundaries.append(zone.lower)
                    if zone.upper > entry:
                        boundaries.append(zone.upper)
                else:
                    if zone.lower < entry:
                        boundaries.append(zone.lower)
                    if zone.upper < entry:
                        boundaries.append(zone.upper)

        return tuple(boundaries)

    @staticmethod
    def _rejected(
        decision_id: str,
        requested_risk: Decimal,
        reason: str,
        *,
        structural_stop_loss: Decimal | None = None,
        final_stop_loss: Decimal | None = None,
        stop_distance: Decimal | None = None,
    ) -> RiskResult:
        return RiskResult(
            decision_id=decision_id,
            requested_risk=requested_risk,
            approved_risk=None,
            position_size=None,
            entry_assumption=None,
            structural_stop_loss=structural_stop_loss,
            final_stop_loss=final_stop_loss,
            target_price=None,
            stop_distance=stop_distance,
            target_distance=None,
            risk_reward=None,
            risk_amount=None,
            status=RiskStatus.RISK_REJECTED,
            reason_codes=(reason,),
        )


__all__ = ["FIXED_RISK_RATE", "MIN_RISK_REWARD", "RISK_VERSION", "RiskEngine"]
