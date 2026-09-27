"""MS-0.18 scheduler tests."""

from datetime import datetime, timedelta, timezone
from threading import Event
from time import sleep

from trading_system.runtime.scheduler import RuntimeScheduler

TS = datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc)


class Clock:
    def __init__(self, value):
        self.value = value

    def __call__(self):
        return self.value


def test_scheduler_invokes_configured_instruments_sequentially_and_once_per_boundary():
    calls = []
    stop_after = Event()

    def next_invocation_at(instrument, now):
        return TS

    def run_if_due(instrument, now):
        calls.append(instrument)
        if len(calls) == 2:
            stop_after.set()

    scheduler = RuntimeScheduler(
        instruments=("EURUSD", "GBPUSD"),
        next_invocation_at=next_invocation_at,
        run_if_due=run_if_due,
        clock=Clock(TS),
    )
    scheduler.start()
    stop_after.wait(timeout=2)
    scheduler.stop()

    assert calls == ["EURUSD", "GBPUSD"]


def test_scheduler_does_not_replay_a_missed_boundary():
    calls = []
    state = {"now": TS + timedelta(hours=2)}

    def next_invocation_at(instrument, now):
        return TS

    def run_if_due(instrument, now):
        calls.append(instrument)

    scheduler = RuntimeScheduler(
        instruments=("EURUSD", "GBPUSD"),
        next_invocation_at=next_invocation_at,
        run_if_due=run_if_due,
        clock=lambda: state["now"],
    )
    scheduler.start()
    sleep(0.05)
    scheduler.stop()

    assert calls == ["EURUSD", "GBPUSD"]


def test_scheduler_isolates_one_instrument_failure():
    calls = []
    stop_after = Event()

    def next_invocation_at(instrument, now):
        return TS

    def run_if_due(instrument, now):
        calls.append(instrument)
        if instrument == "EURUSD":
            raise RuntimeError("provider unavailable")
        stop_after.set()

    scheduler = RuntimeScheduler(
        instruments=("EURUSD", "GBPUSD"),
        next_invocation_at=next_invocation_at,
        run_if_due=run_if_due,
        clock=Clock(TS),
    )
    scheduler.start()
    stop_after.wait(timeout=2)
    scheduler.stop()

    assert calls == ["EURUSD", "GBPUSD"]


def test_scheduler_waits_for_future_operational_boundary():
    calls = []
    future = TS + timedelta(seconds=0.05)

    def next_invocation_at(instrument, now):
        return future

    def run_if_due(instrument, now):
        calls.append(instrument)

    scheduler = RuntimeScheduler(
        instruments=("EURUSD",),
        next_invocation_at=next_invocation_at,
        run_if_due=run_if_due,
        clock=Clock(TS),
    )
    scheduler.start()
    sleep(0.01)
    assert calls == []
    scheduler.stop()
