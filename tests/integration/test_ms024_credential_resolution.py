"""MS-0.24 composition-boundary tests."""

from datetime import datetime, timezone

import pytest

from trading_system.application.composition import (
    CompositionDependencies,
    CompositionGapError,
    compose_runtime,
)
from trading_system.domain import QualificationContextResult, QualificationContextStatus
from trading_system.runtime import (
    DataProviderConfig,
    EnvironmentCredentialResolver,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)

NOW = datetime(2026, 10, 4, 12, 0, tzinfo=timezone.utc)


class Qualification:
    def qualify(self, *, candidate, key_levels, structure, boundary, qualification_timestamp):
        return QualificationContextResult(
            status=QualificationContextStatus.UNAVAILABLE,
            qualification_timestamp=qualification_timestamp,
            risk_request=None,
            governance_request=None,
            reason_codes=("TEST_CONTEXT",),
        )


def config(tmp_path):
    return RuntimeConfig(
        runtime_id="ms024-test",
        instruments=InstrumentConfig(("EURUSD",)),
        operational_time=OperationalTimeConfig(),
        data_provider=DataProviderConfig(
            provider="twelve_data",
            credential_ref="env:TWELVE_DATA_API_KEY",
            symbol_mappings=(("EURUSD", "EUR/USD"),),
        ),
        persistence=PersistenceConfig(
            repository_ref="sqlite-observation",
            storage_location=f"sqlite://{tmp_path / 'observations.sqlite3'}",
        ),
    )


def dependencies(resolver):
    return CompositionDependencies(
        credential_resolver=resolver,
        history_window_resolver=lambda instrument, boundary: object(),
        qualification_context=Qualification(),
    )


def test_composition_accepts_named_credential_resolver(tmp_path):
    runtime = compose_runtime(
        config(tmp_path),
        dependencies=dependencies(
            EnvironmentCredentialResolver({"TWELVE_DATA_API_KEY": "test-key"})
        ),
        clock=lambda: NOW,
    )
    assert runtime.runtime_id == "ms024-test"


def test_composition_rejects_unresolved_credential(tmp_path):
    with pytest.raises(CompositionGapError, match="credential resolution failed: unresolved credential reference"):
        compose_runtime(
            config(tmp_path),
            dependencies=dependencies(EnvironmentCredentialResolver({})),
            clock=lambda: NOW,
        )
