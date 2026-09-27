"""MS-0.15 SQLite observation persistence tests."""

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from trading_system.adapters.observation_sqlite import (
    OBSERVATION_SCHEMA_VERSION,
    ObservationPersistenceError,
    ObservationSchemaMismatch,
    SQLiteObservationRepository,
)
from trading_system.domain import (
    CandidateOutcome,
    ConfirmationType,
    DecisionCandidate,
    DecisionResult,
    DecisionStatus,
    Direction,
    GovernanceResult,
    GovernanceStatus,
    KeyLevel,
    KeyLevelSource,
    ObservationDataWindow,
    ObservationIdentity,
    ObservationRevision,
    ObservationStatus,
    PriceZone,
    RiskResult,
    RiskStatus,
)
from trading_system.observation.repository import ObservationRevisionConflict

UTC = timezone.utc
BOUNDARY = datetime(2026, 9, 27, 10, 0, tzinfo=UTC)


def identity() -> ObservationIdentity:
    return ObservationIdentity("EURUSD", BOUNDARY)


def revision(number: int, status=ObservationStatus.EVALUATED) -> ObservationRevision:
    candidate = DecisionCandidate(
        decision_id=f"D-{number}",
        strategy_version="MS-0.3",
        symbol="EURUSD",
        direction=Direction.BUY,
        setup_type=ConfirmationType.CP1,
        setup_id=f"S-{number}",
        signal_timestamp=BOUNDARY,
        signal_entry_price=Decimal("1.1000"),
        proposed_stop_loss=Decimal("1.0950"),
        proposed_target=Decimal("1.1100"),
        evidence_refs=("candidate-ref",),
    )
    risk = RiskResult(
        decision_id=candidate.decision_id,
        requested_risk=Decimal("0.01"),
        approved_risk=Decimal("0.01"),
        position_size=Decimal("1000"),
        entry_assumption=Decimal("1.1000"),
        structural_stop_loss=Decimal("1.0950"),
        final_stop_loss=Decimal("1.0949"),
        target_price=Decimal("1.1102"),
        stop_distance=Decimal("0.0051"),
        target_distance=Decimal("0.0102"),
        risk_reward=Decimal("2"),
        risk_amount=Decimal("100"),
        status=RiskStatus.RISK_AUTHORIZED,
        reason_codes=("RISK_AUTHORIZED",),
    )
    governance = GovernanceResult(
        decision_id=candidate.decision_id,
        instrument_session_eligible=True,
        daily_trade_count=0,
        daily_loss_count=0,
        checks=("SESSION_ELIGIBLE",),
        status=GovernanceStatus.GOVERNANCE_AUTHORIZED,
        reason_codes=("GOVERNANCE_AUTHORIZED",),
    )
    decision = DecisionResult(
        decision_id=candidate.decision_id,
        status=DecisionStatus.VALID,
        reason_codes=("RISK_AUTHORIZED", "GOVERNANCE_AUTHORIZED"),
    )
    return ObservationRevision(
        identity=identity(),
        revision_number=number,
        evaluation_timestamp=BOUNDARY + timedelta(minutes=5),
        status=status,
        reason="EVALUATION_COMPLETED" if status is ObservationStatus.EVALUATED else "TEST",
        methodology_versions=(("observation", "MS-0.14"), ("structure", "MS-0.1A")),
        data_window=ObservationDataWindow(
            h1_start=BOUNDARY - timedelta(hours=4),
            h1_end=BOUNDARY,
            m15_start=BOUNDARY - timedelta(hours=2),
            m15_end=BOUNDARY,
        ),
        h1_data_reference="h1-ref",
        m15_data_reference="m15-ref",
        validation_outcome=(("H1", "VALID"), ("M15", "VALID")),
        market_structure=None,
        key_levels=(
            KeyLevel(
                key_level_id="KL-1",
                source_types=(KeyLevelSource.VALIDATED_SWING,),
                source_zones=(
                    (KeyLevelSource.VALIDATED_SWING, PriceZone(Decimal("1.098"), Decimal("1.100"))),
                ),
                active=True,
                role=None,
                created_at=BOUNDARY,
                updated_at=BOUNDARY,
                evidence_refs=("kl-ref",),
                state_history=("ACTIVE",),
            ),
        ),
        candidate_outcomes=(
            CandidateOutcome(
                candidate=candidate,
                risk_result=risk,
                governance_result=governance,
                decision_result=decision,
            ),
        ),
        provenance_refs=("provider-ref",),
    )


def test_initializes_numbered_schema_and_persists_revision(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")
    result = db.append(revision(1))

    assert result.revision is not None
    assert result.revision.revision_number == 1
    assert db.latest(identity()).revision == revision(1)


def test_append_is_append_only_and_latest_returns_highest_revision(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")
    db.append(revision(1))
    db.append(revision(2))

    latest = db.latest(identity())

    assert latest is not None
    assert latest.revision is not None
    assert latest.revision.revision_number == 2


def test_duplicate_revision_is_a_recoverable_conflict(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")
    db.append(revision(1))

    with pytest.raises(ObservationRevisionConflict):
        db.append(revision(1))


def test_concurrent_same_revision_allows_one_winner(tmp_path):
    path = tmp_path / "observation.db"

    def append_once():
        return SQLiteObservationRepository(path).append(revision(1))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: _append_result(append_once), range(2)))

    successes = [x for x in results if x is True]
    conflicts = [x for x in results if x is False]
    assert len(successes) == 1
    assert len(conflicts) == 1


def _append_result(fn):
    try:
        fn()
        return True
    except ObservationRevisionConflict:
        return False


def test_database_enforces_revision_number_positive(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")

    with pytest.raises(ValueError):
        invalid = revision(1)
        object.__setattr__(invalid, "revision_number", 0)
        db.append(invalid)


def test_historical_snapshot_reconstructs_complete_canonical_revision(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")
    original = revision(1)
    db.append(original)

    restored = db.latest(identity())

    assert restored is not None
    assert restored.revision == original
    assert restored.revision is not original


def test_future_observation_schema_is_rejected(tmp_path):
    db = SQLiteObservationRepository(tmp_path / "observation.db")
    db.append(revision(1))

    import sqlite3

    with sqlite3.connect(tmp_path / "observation.db") as raw:
        raw.execute(
            "UPDATE observation_revisions SET schema_version=?",
            ("MS-99.0",),
        )
        raw.commit()

    with pytest.raises(ObservationSchemaMismatch):
        db.latest(identity())


def test_repository_io_failure_is_not_an_observation_outcome(tmp_path):
    bad_path = tmp_path / "not-a-file"
    bad_path.mkdir()
    with pytest.raises(ObservationPersistenceError):
        SQLiteObservationRepository(bad_path)

def test_database_contains_hybrid_envelope_and_snapshot(tmp_path):
    db_path = tmp_path / "observation.db"
    SQLiteObservationRepository(db_path).append(revision(1))

    import sqlite3

    with sqlite3.connect(db_path) as raw:
        columns = {
            row[1] for row in raw.execute("PRAGMA table_info(observation_revisions)")
        }
        row = raw.execute(
            "SELECT instrument, h1_boundary_timestamp, revision_number, "
            "status, reason, evaluation_timestamp, snapshot_json, schema_version "
            "FROM observation_revisions"
        ).fetchone()

    assert {
        "observation_id",
        "instrument",
        "h1_boundary_timestamp",
        "revision_number",
        "status",
        "reason",
        "evaluation_timestamp",
        "snapshot_json",
        "schema_version",
    } <= columns
    assert row[0] == "EURUSD"
    assert row[2] == 1
    assert row[7] == OBSERVATION_SCHEMA_VERSION
    assert '"decision_id":"D-1"' in row[6]
