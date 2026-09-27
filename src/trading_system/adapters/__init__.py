"""External system adapters."""

from .observation_sqlite import (
    DATABASE_SCHEMA_VERSION, OBSERVATION_SCHEMA_VERSION,
    ObservationPersistenceError, ObservationRevisionConflict,
    ObservationSchemaMismatch, ObservationSerializationError,
    SQLiteObservationRepository,
)

__all__ = [
    "DATABASE_SCHEMA_VERSION", "OBSERVATION_SCHEMA_VERSION",
    "ObservationPersistenceError", "ObservationRevisionConflict",
    "ObservationSchemaMismatch", "ObservationSerializationError",
    "SQLiteObservationRepository",
]
