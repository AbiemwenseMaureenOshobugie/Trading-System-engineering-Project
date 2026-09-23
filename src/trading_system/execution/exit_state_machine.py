"""Canonical MS-0.10 exit lifecycle."""
from trading_system.domain import ExitExecutionState

class InvalidExitExecutionTransition(ValueError):
    pass

class ExitExecutionStateMachine:
    _ALLOWED = {
        ExitExecutionState.CREATED: frozenset({ExitExecutionState.AUTHORIZED}),
        ExitExecutionState.AUTHORIZED: frozenset({ExitExecutionState.SUBMITTED}),
        ExitExecutionState.SUBMITTED: frozenset({ExitExecutionState.FILLED, ExitExecutionState.FAILED}),
        ExitExecutionState.FILLED: frozenset(),
        ExitExecutionState.FAILED: frozenset(),
    }
    @classmethod
    def transition(cls, current, target):
        if target not in cls._ALLOWED[current]:
            raise InvalidExitExecutionTransition(f"invalid exit execution transition: {current} -> {target}")
        return target
