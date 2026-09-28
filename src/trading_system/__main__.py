"""ASTER runtime entrypoint.

The entrypoint delegates construction to the single MS-0.20 composition root.
"""

from __future__ import annotations

import os
import sys

from trading_system.application.composition import (
    CompositionDependencies,
    CompositionGapError,
    compose_runtime,
)
from trading_system.runtime import (
    DataProviderConfig,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)


def _runtime_config_from_environment() -> RuntimeConfig:
    instruments = tuple(
        value.strip().upper()
        for value in os.environ.get("ASTER_INSTRUMENTS", "EURUSD,GBPUSD").split(",")
        if value.strip()
    )
    return RuntimeConfig(
        runtime_id=os.environ.get("ASTER_RUNTIME_ID", "aster-runtime"),
        instruments=InstrumentConfig(instruments),
        operational_time=OperationalTimeConfig(
            timezone=os.environ.get("ASTER_TIMEZONE", "UTC")
        ),
        data_provider=DataProviderConfig(
            provider=os.environ.get("ASTER_DATA_PROVIDER", "twelve_data"),
            credential_ref=os.environ.get(
                "ASTER_CREDENTIAL_REF", "env:TWELVE_DATA_API_KEY"
            ),
            symbol_mappings=(
                ("EURUSD", "EUR/USD"),
                ("GBPUSD", "GBP/USD"),
            ),
            endpoint=os.environ.get("ASTER_DATA_ENDPOINT"),
        ),
        persistence=PersistenceConfig(
            repository_ref="sqlite-observation",
            storage_location=os.environ.get(
                "ASTER_OBSERVATION_DB", "sqlite://.aster/observations.sqlite3"
            ),
        ),
    )


def _credential_resolver(reference: str) -> str:
    if reference.startswith("env:"):
        name = reference.removeprefix("env:")
        value = os.environ.get(name)
        if value:
            return value
    raise CompositionGapError((f"unresolved credential reference: {reference}",))


def main() -> int:
    try:
        config = _runtime_config_from_environment()
        # The business-specific capabilities remain explicit until their
        # production contracts are implemented. No fake implementations are
        # installed by the entrypoint.
        raise CompositionGapError(
            (
                "governing_key_level_selection",
                "setup_classification",
                "risk_governance_qualification_context",
                "observation_history_policy",
            )
        )
    except CompositionGapError as exc:
        print("ASTER runtime composition gap:", *exc.args[0], sep=" ", file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
