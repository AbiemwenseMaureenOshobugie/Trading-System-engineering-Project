"""MS-0.17 runtime configuration contract tests."""

from datetime import timedelta

import pytest

from trading_system.runtime.config import (
    DataProviderConfig,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)


def test_runtime_configuration_has_four_operational_categories():
    config = RuntimeConfig(
        runtime_id="aster",
        instruments=InstrumentConfig(("EURUSD", "GBPUSD")),
        operational_time=OperationalTimeConfig(),
        data_provider=DataProviderConfig("twelve_data", "secret://twelve"),
        persistence=PersistenceConfig("observation-repository", "sqlite:///aster.db"),
    )
    assert config.runtime_id == "aster"
    assert config.operational_time.poll_offset == timedelta(seconds=30)


@pytest.mark.parametrize(
    "factory",
    [
        lambda: InstrumentConfig(()),
        lambda: OperationalTimeConfig(poll_offset=timedelta(seconds=-1)),
        lambda: DataProviderConfig("", "secret://x"),
        lambda: PersistenceConfig("", "sqlite:///aster.db"),
        lambda: RuntimeConfig(
            "aster",
            InstrumentConfig(("EURUSD",)),
            OperationalTimeConfig(),
            DataProviderConfig("twelve_data", "secret://x"),
            PersistenceConfig("repo", "sqlite:///aster.db"),
        ),
    ],
)
def test_invalid_operational_configuration_is_rejected(factory):
    with pytest.raises(ValueError):
        factory()
