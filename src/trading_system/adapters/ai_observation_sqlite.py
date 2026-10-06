"""SQLite persistence for canonical AI observations."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

from trading_system.domain import (
    AIObservation,
    AIObservationConsumer,
    AIObservationStatus,
)


AI_OBSERVATION_SCHEMA_VERSION = "AI-0.1"


class AIObservationPersistenceError(RuntimeError):
    """Base error for AI observation persistence failures."""


class SQLiteAIObservationRepository:
    """SQLite adapter for the append-only AIObservation contract."""

    def __init__(self, database_path: str | Path, *, timeout: float = 5.0) -> None:
        self._database_path = str(database_path)
        self._timeout = timeout
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self._database_path, timeout=self._timeout)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        try:
            with self._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS ai_observations (
                        observation_id TEXT PRIMARY KEY,
                        status TEXT NOT NULL,
                        model_id TEXT NOT NULL,
                        model_version TEXT NOT NULL,
                        requested_at TEXT NOT NULL,
                        completed_at TEXT,
                        consumer TEXT NOT NULL,
                        context_fingerprint TEXT NOT NULL,
                        schema_version TEXT NOT NULL,
                        snapshot_json TEXT NOT NULL
                    )
                    """
                )
        except sqlite3.Error as exc:
            raise AIObservationPersistenceError(str(exc)) from exc

    @staticmethod
    def _encode_value(value: object) -> object:
        if isinstance(value, Decimal):
            return str(value)
        if isinstance(value, datetime):
            return value.isoformat()
        if hasattr(value, "value"):
            return value.value
        if isinstance(value, tuple):
            return [SQLiteAIObservationRepository._encode_value(item) for item in value]
        return value

    @classmethod
    def _snapshot(cls, observation: AIObservation) -> str:
        payload = asdict(observation)
        return json.dumps(
            {key: cls._encode_value(value) for key, value in payload.items()},
            sort_keys=True,
            separators=(",", ":"),
        )

    @staticmethod
    def _decode_snapshot(payload: str) -> AIObservation:
        data = json.loads(payload)
        data["status"] = AIObservationStatus(data["status"])
        data["consumer"] = AIObservationConsumer(data["consumer"])
        data["requested_at"] = datetime.fromisoformat(data["requested_at"])
        if data["completed_at"] is not None:
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        data["input_references"] = tuple(data["input_references"])
        data["aster_state_references"] = tuple(data["aster_state_references"])
        data["observations"] = tuple(data["observations"])
        data["limitations"] = tuple(data["limitations"])
        if data["confidence"] is not None:
            data["confidence"] = Decimal(data["confidence"])
        return AIObservation(**data)

    def append(self, observation: AIObservation) -> None:
        try:
            snapshot = self._snapshot(observation)
            with self._connect() as connection:
                connection.execute(
                    """
                    INSERT INTO ai_observations (
                        observation_id, status, model_id, model_version,
                        requested_at, completed_at, consumer,
                        context_fingerprint, schema_version, snapshot_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        observation.observation_id,
                        observation.status.value,
                        observation.model_id,
                        observation.model_version,
                        observation.requested_at.isoformat(),
                        observation.completed_at.isoformat()
                        if observation.completed_at is not None
                        else None,
                        observation.consumer.value,
                        observation.context_fingerprint,
                        observation.schema_version,
                        snapshot,
                    ),
                )
        except sqlite3.IntegrityError as exc:
            raise AIObservationPersistenceError(
                f"observation_id already exists: {observation.observation_id}"
            ) from exc
        except sqlite3.Error as exc:
            raise AIObservationPersistenceError(str(exc)) from exc

    def get(self, observation_id: str) -> AIObservation | None:
        try:
            with self._connect() as connection:
                row = connection.execute(
                    "SELECT snapshot_json FROM ai_observations WHERE observation_id = ?",
                    (observation_id,),
                ).fetchone()
        except sqlite3.Error as exc:
            raise AIObservationPersistenceError(str(exc)) from exc
        if row is None:
            return None
        return self._decode_snapshot(row["snapshot_json"])
