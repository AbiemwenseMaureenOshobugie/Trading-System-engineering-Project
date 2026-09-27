"""SQLite durable adapter for MS-0.14 observations."""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_system.domain import (
    CandidateOutcome, ConfirmationType, DecisionCandidate, DecisionResult,
    DecisionStatus, Direction, GovernanceResult, GovernanceStatus, KeyLevel,
    KeyLevelSource, MarketStructureState, ObservationDataWindow,
    ObservationIdentity, ObservationResult, ObservationRevision,
    ObservationStatus, PriceZone, Regime, RiskResult, RiskStatus,
    SwingKind, SwingPoint,
)

DATABASE_SCHEMA_VERSION = 1
OBSERVATION_SCHEMA_VERSION = "MS-0.14"


class ObservationPersistenceError(RuntimeError):
    """Base class for durable observation persistence failures."""


class ObservationRevisionConflict(ObservationPersistenceError):
    """Expected concurrent use of an already-occupied revision."""


class ObservationSchemaMismatch(ObservationPersistenceError):
    """The database or snapshot uses an unsupported schema version."""


class ObservationSerializationError(ObservationPersistenceError):
    """A durable snapshot cannot be reconstructed as a canonical revision."""


MIGRATIONS = (
    (1, "initial_observation_revisions", """
        CREATE TABLE observation_revisions (
            observation_id TEXT NOT NULL,
            instrument TEXT NOT NULL,
            h1_boundary_timestamp TEXT NOT NULL,
            revision_number INTEGER NOT NULL CHECK (revision_number >= 1),
            status TEXT NOT NULL,
            reason TEXT NOT NULL,
            evaluation_timestamp TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            schema_version TEXT NOT NULL,
            PRIMARY KEY (observation_id, revision_number),
            UNIQUE (instrument, h1_boundary_timestamp, revision_number)
        );
        CREATE INDEX idx_observation_revisions_identity
        ON observation_revisions (
            instrument, h1_boundary_timestamp, revision_number DESC
        );
    """),
)


class SQLiteObservationRepository:
    """SQLite implementation of ObservationRepositoryPort."""

    def __init__(self, database_path: str | Path, *, timeout: float = 5.0) -> None:
        self._path = Path(database_path)
        self._timeout = timeout
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def latest(self, identity: ObservationIdentity) -> ObservationResult | None:
        try:
            with self._connect() as db:
                row = db.execute(
                    """SELECT snapshot_json, schema_version
                       FROM observation_revisions
                       WHERE instrument=? AND h1_boundary_timestamp=?
                       ORDER BY revision_number DESC LIMIT 1""",
                    (identity.instrument, _dt(identity.h1_boundary_timestamp)),
                ).fetchone()
            if row is None:
                return None
            if row["schema_version"] != OBSERVATION_SCHEMA_VERSION:
                raise ObservationSchemaMismatch(
                    f"unsupported observation schema: {row['schema_version']}"
                )
            revision = _from_json(row["snapshot_json"])
            if revision.identity != identity:
                raise ObservationSerializationError("persisted identity mismatch")
            return ObservationResult(
                status=revision.status, reason=revision.reason,
                identity=identity, revision=revision,
            )
        except ObservationPersistenceError:
            raise
        except (sqlite3.Error, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ObservationPersistenceError(
                f"failed to read observation history: {exc}"
            ) from exc

    def append(self, revision: ObservationRevision) -> ObservationResult:
        snapshot = _to_json(revision)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                try:
                    db.execute(
                        """INSERT INTO observation_revisions
                        (observation_id,instrument,h1_boundary_timestamp,
                         revision_number,status,reason,evaluation_timestamp,
                         snapshot_json,schema_version)
                        VALUES (?,?,?,?,?,?,?,?,?)""",
                        (
                            _identity(revision.identity),
                            revision.identity.instrument,
                            _dt(revision.identity.h1_boundary_timestamp),
                            revision.revision_number,
                            revision.status.value,
                            revision.reason,
                            _dt(revision.evaluation_timestamp),
                            snapshot,
                            OBSERVATION_SCHEMA_VERSION,
                        ),
                    )
                    db.commit()
                except sqlite3.IntegrityError as exc:
                    db.rollback()
                    if "unique" in str(exc).lower() or "primary key" in str(exc).lower():
                        raise ObservationRevisionConflict(
                            f"revision already exists: {revision.identity.instrument} "
                            f"{revision.identity.h1_boundary_timestamp.isoformat()} "
                            f"revision={revision.revision_number}"
                        ) from exc
                    raise ObservationPersistenceError(str(exc)) from exc
                except sqlite3.Error:
                    db.rollback()
                    raise
            return ObservationResult(
                status=revision.status, reason=revision.reason,
                identity=revision.identity, revision=revision,
            )
        except ObservationPersistenceError:
            raise
        except sqlite3.Error as exc:
            raise ObservationPersistenceError(
                f"failed to persist observation revision: {exc}"
            ) from exc

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self._path, timeout=self._timeout, isolation_level=None)
        db.row_factory = sqlite3.Row
        return db

    def _initialize(self) -> None:
        try:
            with self._connect() as db:
                db.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
                    version INTEGER PRIMARY KEY,
                    name TEXT NOT NULL UNIQUE,
                    applied_at TEXT NOT NULL
                )""")
                applied = {r[0] for r in db.execute(
                    "SELECT version FROM schema_migrations"
                )}
                known = {m[0] for m in MIGRATIONS}
                if applied - known:
                    raise ObservationSchemaMismatch(
                        f"unsupported database migrations: {sorted(applied-known)}"
                    )
                for version, name, sql in MIGRATIONS:
                    if version not in applied:
                        db.executescript(sql)
                        db.execute(
                            "INSERT INTO schema_migrations VALUES (?,?,?)",
                            (version, name, _dt(datetime.now().astimezone())),
                        )
                db.commit()
        except ObservationPersistenceError:
            raise
        except sqlite3.Error as exc:
            raise ObservationPersistenceError(
                f"failed to initialize observation database: {exc}"
            ) from exc


def _dt(value: datetime) -> str:
    if value.tzinfo is None:
        raise ValueError("persisted datetime must be timezone-aware")
    return value.isoformat()


def _identity(value: ObservationIdentity) -> str:
    return f"{value.instrument}|{_dt(value.h1_boundary_timestamp)}"


def _to_json(revision: ObservationRevision) -> str:
    return json.dumps(asdict(revision), default=_json_default,
                      sort_keys=True, separators=(",", ":"))


def _json_default(value: Any) -> Any:
    if isinstance(value, datetime):
        return _dt(value)
    if isinstance(value, Decimal):
        return {"__decimal__": str(value)}
    if hasattr(value, "value"):
        return value.value
    raise TypeError(f"unsupported snapshot value: {type(value)!r}")


def _decimal(value: Any) -> Decimal | None:
    if value is None:
        return None
    if isinstance(value, dict) and "__decimal__" in value:
        return Decimal(value["__decimal__"])
    return Decimal(value)


def _zone(v: dict[str, Any]) -> PriceZone:
    return PriceZone(_decimal(v["lower"]), _decimal(v["upper"]))


def _swing(v: dict[str, Any]) -> SwingPoint:
    return SwingPoint(_dt_parse(v["timestamp"]), _decimal(v["price"]), SwingKind(v["kind"]))


def _structure(v: dict[str, Any] | None) -> MarketStructureState | None:
    if v is None:
        return None
    return MarketStructureState(
        regime=Regime(v["regime"]),
        structure_version=v["structure_version"],
        meaningful_highs=tuple(_swing(x) for x in v["meaningful_highs"]),
        meaningful_lows=tuple(_swing(x) for x in v["meaningful_lows"]),
        controlling_level=_swing(v["controlling_level"]) if v["controlling_level"] else None,
        range_upper_boundary=_zone(v["range_upper_boundary"]) if v["range_upper_boundary"] else None,
        range_lower_boundary=_zone(v["range_lower_boundary"]) if v["range_lower_boundary"] else None,
        structural_events=tuple(v["structural_events"]),
        evaluated_at=_dt_parse(v["evaluated_at"]),
    )


def _key_level(v: dict[str, Any]) -> KeyLevel:
    return KeyLevel(
        key_level_id=v["key_level_id"],
        source_types=tuple(KeyLevelSource(x) for x in v["source_types"]),
        source_zones=tuple(
            (KeyLevelSource(x["source_type"]), _zone(x["zone"]))
            for x in v["source_zones"]
        ),
        active=v["active"], role=v["role"],
        created_at=_dt_parse(v["created_at"]),
        updated_at=_dt_parse(v["updated_at"]),
        evidence_refs=tuple(v["evidence_refs"]),
        state_history=tuple(v["state_history"]),
    )


def _candidate(v: dict[str, Any]) -> DecisionCandidate:
    return DecisionCandidate(
        decision_id=v["decision_id"], strategy_version=v["strategy_version"],
        symbol=v["symbol"], direction=Direction(v["direction"]),
        setup_type=ConfirmationType(v["setup_type"]), setup_id=v["setup_id"],
        signal_timestamp=_dt_parse(v["signal_timestamp"]),
        signal_entry_price=_decimal(v["signal_entry_price"]),
        proposed_stop_loss=_decimal(v["proposed_stop_loss"]),
        proposed_target=_decimal(v["proposed_target"]),
        evidence_refs=tuple(v["evidence_refs"]),
    )


def _risk(v: dict[str, Any] | None) -> RiskResult | None:
    if v is None:
        return None
    names = (
        "requested_risk","approved_risk","position_size","entry_assumption",
        "structural_stop_loss","final_stop_loss","target_price","stop_distance",
        "target_distance","risk_reward","risk_amount",
    )
    return RiskResult(
        decision_id=v["decision_id"],
        **{n: _decimal(v[n]) for n in names},
        status=RiskStatus(v["status"]), reason_codes=tuple(v["reason_codes"]),
    )


def _governance(v: dict[str, Any] | None) -> GovernanceResult | None:
    if v is None:
        return None
    return GovernanceResult(
        decision_id=v["decision_id"],
        instrument_session_eligible=v["instrument_session_eligible"],
        daily_trade_count=v["daily_trade_count"], daily_loss_count=v["daily_loss_count"],
        checks=tuple(v["checks"]), status=GovernanceStatus(v["status"]),
        reason_codes=tuple(v["reason_codes"]),
    )


def _decision(v: dict[str, Any] | None) -> DecisionResult | None:
    if v is None:
        return None
    return DecisionResult(
        decision_id=v["decision_id"], status=DecisionStatus(v["status"]),
        reason_codes=tuple(v["reason_codes"]),
    )


def _outcome(v: dict[str, Any]) -> CandidateOutcome:
    return CandidateOutcome(
        candidate=_candidate(v["candidate"]),
        risk_result=_risk(v["risk_result"]),
        governance_result=_governance(v["governance_result"]),
        decision_result=_decision(v["decision_result"]),
    )


def _from_json(snapshot: str) -> ObservationRevision:
    v = json.loads(snapshot)
    ident = ObservationIdentity(
        v["identity"]["instrument"],
        _dt_parse(v["identity"]["h1_boundary_timestamp"]),
    )
    w = v["data_window"]
    return ObservationRevision(
        identity=ident, revision_number=v["revision_number"],
        evaluation_timestamp=_dt_parse(v["evaluation_timestamp"]),
        status=ObservationStatus(v["status"]), reason=v["reason"],
        methodology_versions=tuple(map(tuple, v["methodology_versions"])),
        data_window=(
            ObservationDataWindow(
                _dt_parse(w["h1_start"]), _dt_parse(w["h1_end"]),
                _dt_parse(w["m15_start"]), _dt_parse(w["m15_end"]),
            ) if w else None
        ),
        h1_data_reference=v["h1_data_reference"],
        m15_data_reference=v["m15_data_reference"],
        validation_outcome=tuple(map(tuple, v["validation_outcome"])),
        market_structure=_structure(v["market_structure"]),
        key_levels=tuple(_key_level(x) for x in v["key_levels"]),
        candidate_outcomes=tuple(_outcome(x) for x in v["candidate_outcomes"]),
        provenance_refs=tuple(v["provenance_refs"]),
    )


def _dt_parse(value: str) -> datetime:
    return datetime.fromisoformat(value)


__all__ = [
    "DATABASE_SCHEMA_VERSION", "OBSERVATION_SCHEMA_VERSION",
    "ObservationPersistenceError", "ObservationRevisionConflict",
    "ObservationSchemaMismatch", "ObservationSerializationError",
    "SQLiteObservationRepository",
]
