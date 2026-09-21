"""Controlled execution boundary for paper, broker, and MT5 adapters."""

from .engine import ExecutionEngine
from .state_machine import ExecutionStateMachine, InvalidExecutionTransition

__all__ = [
    "ExecutionEngine",
    "ExecutionStateMachine",
    "InvalidExecutionTransition",
]
