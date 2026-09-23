"""Deterministic MS-0.10 position/exit management."""

from __future__ import annotations
from datetime import datetime
from typing import Callable
from trading_system.domain import ExitInstruction, ExitType, Position, RiskResult

class ExitManager:
    VERSION = "MS-0.10"
    def __init__(self, *, clock: Callable[[], datetime]) -> None:
        self._clock = clock

    def create_instruction(self, *, position: Position, risk: RiskResult, exit_type: ExitType) -> ExitInstruction:
        if risk.decision_id != position.decision_id:
            raise PermissionError("risk decision_id does not match position")
        trigger_price = risk.final_stop_loss if exit_type is ExitType.STOP_LOSS else risk.target_price if exit_type is ExitType.TARGET else None
        if trigger_price is None:
            raise PermissionError("approved risk geometry has no trigger price")
        return ExitInstruction(
            exit_instruction_id=f"XI-{position.position_id}-{exit_type.value}",
            position_id=position.position_id,
            decision_id=position.decision_id,
            symbol=position.symbol,
            direction=position.direction,
            exit_type=exit_type,
            requested_quantity=position.open_quantity,
            trigger_price=trigger_price,
            created_timestamp=self._clock(),
            source_reference=f"RISK:{risk.decision_id}:{exit_type.value}",
        )
