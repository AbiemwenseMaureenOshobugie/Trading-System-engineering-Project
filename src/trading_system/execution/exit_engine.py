"""Deterministic MS-0.10 paper exit execution."""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Callable
from trading_system.domain import ExitExecutionRecord, ExitExecutionState, ExitInstruction, ExitPaperFill
from .exit_state_machine import ExitExecutionStateMachine

class ExitExecutionEngine:
    VERSION = "MS-0.10"
    def __init__(self, *, clock: Callable[[], datetime] | None = None) -> None:
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def submit(self, *, instruction: ExitInstruction) -> ExitExecutionRecord:
        self._validate(instruction)
        now = self._clock()
        state = ExitExecutionStateMachine.transition(ExitExecutionState.CREATED, ExitExecutionState.AUTHORIZED)
        state = ExitExecutionStateMachine.transition(state, ExitExecutionState.SUBMITTED)
        fill = ExitPaperFill(f"XF-{instruction.exit_instruction_id}", instruction.exit_instruction_id,
                             instruction.trigger_price, instruction.requested_quantity, now)
        state = ExitExecutionStateMachine.transition(state, ExitExecutionState.FILLED)
        return ExitExecutionRecord(f"XE-{instruction.exit_instruction_id}", instruction.position_id,
            instruction.decision_id, state, instruction, fill, None, None)

    def fail(self, *, instruction: ExitInstruction, failure_reason: str) -> ExitExecutionRecord:
        if not failure_reason.strip():
            raise ValueError("failure_reason must not be empty")
        self._validate(instruction)
        now = self._clock()
        state = ExitExecutionStateMachine.transition(ExitExecutionState.CREATED, ExitExecutionState.AUTHORIZED)
        state = ExitExecutionStateMachine.transition(state, ExitExecutionState.SUBMITTED)
        state = ExitExecutionStateMachine.transition(state, ExitExecutionState.FAILED)
        return ExitExecutionRecord(f"XE-{instruction.exit_instruction_id}", instruction.position_id,
            instruction.decision_id, state, instruction, None, failure_reason, now)

    @staticmethod
    def _validate(instruction: ExitInstruction) -> None:
        if instruction.requested_quantity <= 0:
            raise PermissionError("exit quantity must be positive")
        if instruction.created_timestamp.tzinfo is None:
            raise PermissionError("exit instruction timestamp must be timezone-aware")
