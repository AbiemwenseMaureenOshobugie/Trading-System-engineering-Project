"""MS-0.16 lifecycle coordinator tests."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from trading_system.domain import ObservationIdentity, ObservationStatus
from trading_system.observation.coordinator import (
    DEFAULT_POLL_OFFSET,
    ObservationLifecycleCoordinator,
)

BOUNDARY = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, value):
        self.value = value

    def now(self):
        return self.value


class Boundary:
    def latest_completed_boundary(self, *, instrument, now):
        return BOUNDARY


class Repository:
    def __init__(self, result=None):
        self.result = result
        self.calls = []

    def latest(self, identity):
        self.calls.append(identity)
        return self.result


class Runner:
    def __init__(self):
        self.calls = []

    def run(self, *, instrument, now=None, observation_boundary=None):
        self.calls.append((instrument, now, observation_boundary))
        return SimpleNamespace(
            status=ObservationStatus.EVALUATED,
            identity=ObservationIdentity(instrument, observation_boundary),
        )


def make_coordinator(repository=None, runner=None, now=BOUNDARY):
    return ObservationLifecycleCoordinator(
        clock=Clock(now),
        boundary_port=Boundary(),
        repository=repository or Repository(),
        runner=runner or Runner(),
    )


def test_next_invocation_at_uses_next_h1_boundary_and_poll_offset():
    c = make_coordinator()
    assert c.next_invocation_at(
        instrument="EURUSD",
        now=BOUNDARY,
    ) == BOUNDARY + DEFAULT_POLL_OFFSET


def test_next_invocation_at_can_return_no_boundary():
    class NoBoundary(Boundary):
        def next_completed_boundary(self, *, instrument, now):
            return None

    c = ObservationLifecycleCoordinator(
        clock=Clock(BOUNDARY),
        boundary_port=NoBoundary(),
        repository=Repository(),
        runner=Runner(),
    )
    assert c.next_invocation_at(instrument="EURUSD", now=BOUNDARY) is None


def test_existing_thirty_second_offset():
    assert make_coordinator(
        now=BOUNDARY + timedelta(seconds=29)
    ).opportunity(instrument="EURUSD") is None

    opportunity = make_coordinator(
        now=BOUNDARY + DEFAULT_POLL_OFFSET
    ).opportunity(instrument="EURUSD")

    assert opportunity is not None
    assert opportunity.invocation_at == BOUNDARY + DEFAULT_POLL_OFFSET


def test_due_invocation_delegates_to_runner():
    runner = Runner()
    c = make_coordinator(
        runner=runner,
        now=BOUNDARY + DEFAULT_POLL_OFFSET,
    )

    result = c.run_if_due(instrument="EURUSD")

    assert result.status is ObservationStatus.EVALUATED
    assert runner.calls == [
        ("EURUSD", BOUNDARY + DEFAULT_POLL_OFFSET, BOUNDARY)
    ]


def test_terminal_identity_is_reused():
    existing = SimpleNamespace(status=ObservationStatus.NO_SETUP)
    runner = Runner()

    result = make_coordinator(
        repository=Repository(existing),
        runner=runner,
        now=BOUNDARY + DEFAULT_POLL_OFFSET,
    ).run_if_due(instrument="EURUSD")

    assert result is existing
    assert runner.calls == []


def test_wait_identity_is_retryable():
    existing = SimpleNamespace(status=ObservationStatus.WAIT)
    runner = Runner()

    make_coordinator(
        repository=Repository(existing),
        runner=runner,
        now=BOUNDARY + DEFAULT_POLL_OFFSET,
    ).run_if_due(instrument="EURUSD")

    assert runner.calls[0][2] == BOUNDARY


def test_new_boundary_is_new_identity():
    class NewBoundary(Boundary):
        def latest_completed_boundary(self, *, instrument, now):
            return BOUNDARY + timedelta(hours=1)

    runner = Runner()
    c = ObservationLifecycleCoordinator(
        clock=Clock(BOUNDARY + timedelta(hours=1, seconds=30)),
        boundary_port=NewBoundary(),
        repository=Repository(),
        runner=runner,
    )

    c.run_if_due(instrument="EURUSD")

    assert runner.calls[0][2] == BOUNDARY + timedelta(hours=1)


def test_manual_invocation_is_explicit():
    runner = Runner()

    make_coordinator(runner=runner).invoke_manual(
        instrument="EURUSD",
        observation_boundary=BOUNDARY,
    )

    assert runner.calls[0][2] == BOUNDARY
