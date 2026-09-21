"""Canonical MS-0.7 execution lifecycle."""

from trading_system.domain import ExecutionState


class InvalidExecutionTransition(ValueError):
    """Raised when an execution attempts an illegal lifecycle transition."""


class ExecutionStateMachine:
    """Enforce the strict forward-only ASTER execution lifecycle."""

    _ALLOWED = {
        ExecutionState.AUTHORIZED: frozenset({ExecutionState.SUBMITTED}),
        ExecutionState.SUBMITTED: frozenset(
            {ExecutionState.FILLED, ExecutionState.FAILED}
        ),
        ExecutionState.FILLED: frozenset(),
        ExecutionState.FAILED: frozenset(),
    }

    @classmethod
    def transition(
        cls, current: ExecutionState, target: ExecutionState
    ) -> ExecutionState:
        if target not in cls._ALLOWED[current]:
            raise InvalidExecutionTransition(
                f"invalid execution transition: {current} -> {target}"
            )
        return target
