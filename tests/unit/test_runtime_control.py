"""MS-0.17 operational-control tests."""

from datetime import datetime, timedelta, timezone
from threading import Event, Thread
from decimal import Decimal

import pytest

from trading_system.domain import ObservationResult, ObservationStatus
from trading_system.runtime.audit import RuntimeAuditRecord
from trading_system.runtime.config import (
    DataProviderConfig,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)
from trading_system.runtime.control import RuntimeControl, RuntimeControlError
from trading_system.runtime.failure import RuntimeFailureComponent
from trading_system.runtime.ownership import RuntimeOwnershipError
from trading_system.runtime.status import RuntimeStatus


TS = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def config():
    return RuntimeConfig(
        runtime_id="aster-test",
        instruments=InstrumentConfig(("EURUSD", "GBPUSD")),
        operational_time=OperationalTimeConfig(),
        data_provider=DataProviderConfig(
            provider="twelve_data",
            credential_ref="secret://twelve-data",
            symbol_mappings=(("EURUSD", "EUR/USD"),),
        ),
        persistence=PersistenceConfig(
            repository_ref="observation-repository",
            storage_location="memory://test",
        ),
    )


class Ownership:
    def __init__(self, fail=False):
        self.fail = fail
        self.acquired = False
    def acquire(self):
        if self.fail:
            raise RuntimeOwnershipError("already owned")
        if self.acquired:
            raise RuntimeOwnershipError("already acquired")
        self.acquired = True
    def release(self):
        self.acquired = False


class Audit:
    def __init__(self):
        self.events: list[RuntimeAuditRecord] = []
    def record(self, event):
        self.events.append(event)


class Coordinator:
    def __init__(self):
        self.manual_calls = 0
        self.due_calls = 0
        self.started = Event()
        self.release = Event()
    def run_if_due(self, *, instrument, now=None):
        self.due_calls += 1
        self.started.set()
        self.release.wait(timeout=2)
        return ObservationResult(
            status=ObservationStatus.NO_SETUP,
            reason="NO_QUALIFYING_SETUP",
            identity=None,
            revision=None,
        )
    def invoke_manual(self, *, instrument, observation_boundary=None, now=None):
        self.manual_calls += 1
        return ObservationResult(
            status=ObservationStatus.NO_SETUP,
            reason="NO_QUALIFYING_SETUP",
            identity=None,
            revision=None,
        )


def control(coordinator=None, ownership=None, audit=None):
    return RuntimeControl(
        config=config(),
        ownership=ownership or Ownership(),
        coordinator=coordinator or Coordinator(),
        audit_port=audit or Audit(),
        clock=lambda: TS,
    )


def test_start_acquires_ownership_and_enters_running():
    c = control()
    assert c.start() is RuntimeStatus.RUNNING
    assert c.status is RuntimeStatus.RUNNING


def test_ownership_failure_is_runtime_failure_not_observation_wait():
    c = control(ownership=Ownership(fail=True))
    assert c.start() is RuntimeStatus.FAILED
    assert c.last_failure is not None
    assert c.last_failure.component is RuntimeFailureComponent.OWNERSHIP
    assert c.last_failure.failure_code == "OWNERSHIP_REJECTED"


def test_manual_invocation_uses_coordinator_boundary():
    coordinator = Coordinator()
    c = control(coordinator=coordinator)
    c.start()
    result = c.invoke_manual(instrument="EURUSD", observation_boundary=TS)
    assert result.status is ObservationStatus.NO_SETUP
    assert coordinator.manual_calls == 1
    assert coordinator.due_calls == 0


def test_runtime_invocation_uses_run_if_due_boundary():
    coordinator = Coordinator()
    coordinator.release.set()
    c = control(coordinator=coordinator)
    c.start()
    result = c.run_if_due(instrument="EURUSD")
    assert result.status is ObservationStatus.NO_SETUP
    assert coordinator.due_calls == 1


def test_stop_waits_for_in_flight_invocation_before_releasing_ownership():
    coordinator = Coordinator()
    c = control(coordinator=coordinator)
    c.start()

    worker = Thread(target=lambda: c.run_if_due(instrument="EURUSD"))
    worker.start()
    assert coordinator.started.wait(timeout=2)

    stopper_done = Event()
    def stopper():
        c.stop()
        stopper_done.set()
    stopper_thread = Thread(target=stopper)
    stopper_thread.start()

    assert not stopper_done.wait(timeout=0.1)
    assert c.status is RuntimeStatus.STOPPING

    coordinator.release.set()
    worker.join(timeout=2)
    assert stopper_done.wait(timeout=2)
    stopper_thread.join(timeout=2)
    assert c.status is RuntimeStatus.STOPPED


def test_manual_invocation_is_blocked_when_not_running():
    c = control()
    with pytest.raises(RuntimeControlError):
        c.invoke_manual(instrument="EURUSD")


def test_observation_failure_becomes_structured_runtime_failure():
    class BrokenCoordinator(Coordinator):
        def run_if_due(self, *, instrument, now=None):
            raise RuntimeError("provider unavailable")
    c = control(coordinator=BrokenCoordinator())
    c.start()
    with pytest.raises(RuntimeError):
        c.run_if_due(instrument="EURUSD")
    assert c.status is RuntimeStatus.FAILED
    assert c.last_failure is not None
    assert c.last_failure.component is RuntimeFailureComponent.COORDINATOR


def test_operational_configuration_excludes_methodology():
    c = config()
    assert c.instruments.instruments == ("EURUSD", "GBPUSD")
    assert c.operational_time.poll_offset == timedelta(seconds=30)
    assert c.data_provider.provider == "twelve_data"
    assert not hasattr(c, "risk_percent")
    assert not hasattr(c, "minimum_rr")
    assert not hasattr(c, "entry_rule")
