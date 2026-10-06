"""MS-0.26 AI/ML bounded contract and persistence tests."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.adapters.ai_observation_sqlite import SQLiteAIObservationRepository
from trading_system.domain import (
    AIObservation,
    AIObservationConsumer,
    AIObservationStatus,
)


NOW = datetime(2026, 10, 6, 12, 0, tzinfo=timezone.utc)


def observation(
    *,
    observation_id: str = "AI-001",
    status: AIObservationStatus = AIObservationStatus.COMPLETED,
    completed_at: datetime | None = NOW,
) -> AIObservation:
    return AIObservation(
        observation_id=observation_id,
        status=status,
        model_id="aster-explanation",
        model_version="0.1.0",
        requested_at=NOW,
        completed_at=completed_at,
        consumer=AIObservationConsumer.EXPLANATION,
        input_references=("OBS-001",),
        aster_state_references=("DEC-001", "RISK-001", "GOV-001"),
        context_fingerprint="ctx-001",
        observations=("M15 structure is consistent with the supplied deterministic state.",),
        confidence=Decimal("0.78"),
        explanation="Advisory interpretation only.",
        limitations=("Snapshot-only context.",),
        failure_category=None,
        schema_version="AI-0.1",
    )


def test_ai_observation_is_advisory_and_versioned() -> None:
    item = observation()
    assert item.status is AIObservationStatus.COMPLETED
    assert item.consumer is AIObservationConsumer.EXPLANATION
    assert item.schema_version == "AI-0.1"
    assert item.aster_state_references == ("DEC-001", "RISK-001", "GOV-001")


def test_non_completed_observation_cannot_have_completion_timestamp() -> None:
    with pytest.raises(ValueError, match="completed_at"):
        observation(
            status=AIObservationStatus.TIMEOUT,
            completed_at=NOW,
        )


def test_non_completed_observation_can_be_persisted_without_completion_timestamp(
    tmp_path,
) -> None:
    repository = SQLiteAIObservationRepository(tmp_path / "ai.sqlite3")
    item = observation(
        observation_id="AI-TIMEOUT",
        status=AIObservationStatus.TIMEOUT,
        completed_at=None,
    )
    repository.append(item)
    assert repository.get("AI-TIMEOUT") == item


def test_each_invocation_has_distinct_identity_even_with_same_context() -> None:
    first = observation(observation_id="AI-001")
    second = observation(observation_id="AI-002")
    assert first.observation_id != second.observation_id
    assert first.context_fingerprint == second.context_fingerprint


def test_retry_is_append_only(tmp_path) -> None:
    repository = SQLiteAIObservationRepository(tmp_path / "ai.sqlite3")
    failed = observation(
        observation_id="AI-FAILED",
        status=AIObservationStatus.FAILED,
        completed_at=None,
    )
    retry = observation(observation_id="AI-RETRY")
    repository.append(failed)
    repository.append(retry)
    assert repository.get("AI-FAILED") == failed
    assert repository.get("AI-RETRY") == retry


def test_duplicate_observation_id_is_rejected(tmp_path) -> None:
    repository = SQLiteAIObservationRepository(tmp_path / "ai.sqlite3")
    repository.append(observation())
    with pytest.raises(RuntimeError, match="already exists"):
        repository.append(observation())


def test_round_trip_preserves_canonical_record(tmp_path) -> None:
    repository = SQLiteAIObservationRepository(tmp_path / "ai.sqlite3")
    item = observation()
    repository.append(item)
    assert repository.get(item.observation_id) == item
