"""Explicit operational configuration for MS-0.17.

No methodology, strategy, risk, governance, or execution rules belong here.
"""

from dataclasses import dataclass
from datetime import timedelta


@dataclass(frozen=True, slots=True)
class InstrumentConfig:
    instruments: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.instruments:
            raise ValueError("at least one instrument is required")
        if any(not instrument.strip() for instrument in self.instruments):
            raise ValueError("instrument names must not be blank")


@dataclass(frozen=True, slots=True)
class OperationalTimeConfig:
    timezone: str = "UTC"
    poll_offset: timedelta = timedelta(seconds=30)

    def __post_init__(self) -> None:
        if not self.timezone.strip():
            raise ValueError("timezone must not be blank")
        if self.poll_offset < timedelta(0):
            raise ValueError("poll_offset must not be negative")


@dataclass(frozen=True, slots=True)
class DataProviderConfig:
    provider: str
    credential_ref: str
    symbol_mappings: tuple[tuple[str, str], ...] = ()
    endpoint: str | None = None

    def __post_init__(self) -> None:
        if not self.provider.strip():
            raise ValueError("provider must not be blank")
        if not self.credential_ref.strip():
            raise ValueError("credential_ref must not be blank")


@dataclass(frozen=True, slots=True)
class PersistenceConfig:
    repository_ref: str
    storage_location: str

    def __post_init__(self) -> None:
        if not self.repository_ref.strip():
            raise ValueError("repository_ref must not be blank")
        if not self.storage_location.strip():
            raise ValueError("storage_location must not be blank")


@dataclass(frozen=True, slots=True)
class RuntimeConfig:
    runtime_id: str
    instruments: InstrumentConfig
    operational_time: OperationalTimeConfig
    data_provider: DataProviderConfig
    persistence: PersistenceConfig

    def __post_init__(self) -> None:
        if not self.runtime_id.strip():
            raise ValueError("runtime_id must not be blank")
