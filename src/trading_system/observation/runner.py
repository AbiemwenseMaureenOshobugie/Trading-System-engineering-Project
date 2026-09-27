
"""MS-0.14 deterministic observation orchestration."""

from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from typing import Callable, Protocol, Sequence

from trading_system.application.ports import (
    AuditPort,
    ConfirmationEnginePort,
    DecisionEnginePort,
    GovernanceEnginePort,
    H1MarketStructurePort,
    KeyLevelEnginePort,
    MarketDataPort,
    ObservationRepositoryPort,
    RiskEnginePort,
    SetupClassifierPort,
)
from trading_system.domain import (
    AuditRecord,
    CandidateOutcome,
    DecisionCandidate,
    DecisionRequest,
    KeyLevel,
    MarketCandle,
    MarketDataQuality,
    ObservationDataWindow,
    ObservationIdentity,
    ObservationReason,
    ObservationResult,
    ObservationRevision,
    ObservationStatus,
    RiskRequest,
    Timeframe,
)
from .repository import ObservationRevisionConflict

MS014_VERSION = "MS-0.14"


class ObservationExecutionError(RuntimeError):
    """Unexpected application/component failure; not an observation outcome."""


class ObservationBoundaryPort(Protocol):
    """Resolve the newest completed H1 boundary."""

    def latest_completed_boundary(
        self, *, instrument: str, now: datetime
    ) -> datetime | None: ...


class ObservationHistoryResolverPort(Protocol):
    """Resolve operational data windows without owning methodology rules."""

    def resolve(
        self, *, instrument: str, h1_boundary: datetime
    ) -> ObservationDataWindow: ...


class ObservationMarketDataPort(MarketDataPort, Protocol):
    """Canonical market data plus provider-neutral quality metadata."""

    def get_quality(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> MarketDataQuality: ...


class ObservationKeyLevelSelectorPort(Protocol):
    """Select governing Key Levels without implementing new methodology."""

    def select(
        self, *, key_levels: Sequence[KeyLevel], structure, direction: str
    ) -> Sequence[KeyLevel]: ...


class ObservationQualificationContextPort(Protocol):
    """Supply already-defined operational inputs required by Risk/Governance."""

    def risk_request(
        self,
        *,
        candidate: DecisionCandidate,
        key_levels: Sequence[KeyLevel],
        boundary: datetime,
    ) -> RiskRequest: ...

    def governance_request(
        self, *, candidate: DecisionCandidate, boundary: datetime
    ): ...


class ObservationRunner:
    """Run one H1-anchored deterministic ASTER observation."""

    def __init__(
        self,
        *,
        market_data: ObservationMarketDataPort,
        boundary_port: ObservationBoundaryPort,
        history_resolver: ObservationHistoryResolverPort,
        structure_engine: H1MarketStructurePort,
        key_level_engine: KeyLevelEnginePort,
        key_level_selector: ObservationKeyLevelSelectorPort,
        confirmation_engine: ConfirmationEnginePort,
        setup_classifier: SetupClassifierPort,
        risk_engine: RiskEnginePort,
        governance_engine: GovernanceEnginePort,
        decision_engine: DecisionEnginePort,
        qualification_context: ObservationQualificationContextPort,
        repository: ObservationRepositoryPort,
        audit_port: AuditPort | None = None,
        methodology_versions: tuple[tuple[str, str], ...] = (),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._market_data = market_data
        self._boundary_port = boundary_port
        self._history = history_resolver
        self._structure = structure_engine
        self._key_levels = key_level_engine
        self._selector = key_level_selector
        self._confirmation = confirmation_engine
        self._classifier = setup_classifier
        self._risk = risk_engine
        self._governance = governance_engine
        self._decision = decision_engine
        self._qualification = qualification_context
        self._repository = repository
        self._audit = audit_port
        self._methodology_versions = methodology_versions
        self._clock = clock or (lambda: datetime.now(timezone.utc))

    def run(
        self,
        *,
        instrument: str,
        now: datetime | None = None,
        observation_boundary: datetime | None = None,
    ) -> ObservationResult:
        now_utc = self._utc(now or self._clock())
        boundary = observation_boundary
        if boundary is None:
            boundary = self._boundary_port.latest_completed_boundary(
                instrument=instrument, now=now_utc
            )
        if boundary is None:
            return ObservationResult(
                status=ObservationStatus.NO_OBSERVATION,
                reason=ObservationReason.NO_NEW_H1_CANDLE.value,
            )

        boundary = self._utc(boundary)
        identity = ObservationIdentity(instrument, boundary)
        existing = self._repository.latest(identity)

        if existing is not None and existing.status in {
            ObservationStatus.EVALUATED,
            ObservationStatus.NO_SETUP,
        }:
            return existing

        revision_number = (
            1 if existing is None or existing.revision is None
            else existing.revision.revision_number + 1
        )
        evaluated_at = self._utc(self._clock())

        try:
            window = self._history.resolve(
                instrument=instrument, h1_boundary=boundary
            )
            data = self._load_data(instrument, window)
            failure_reason = self._data_failure_reason(data)
            if failure_reason is not None:
                return self._persist(
                    self._revision(
                        identity=identity,
                        revision_number=revision_number,
                        evaluation_timestamp=evaluated_at,
                        status=ObservationStatus.WAIT,
                        reason=failure_reason,
                        window=window,
                        data=data,
                    )
                )

            structure = self._structure.evaluate(
                candles=data.h1,
                evaluation_cutoff=boundary,
            )
            key_levels = tuple(
                self._key_levels.detect(candles=data.h1, structure=structure)
            )

            confirmations = []
            for direction in self._directions_from_structure(structure):
                selected = self._selector.select(
                    key_levels=key_levels,
                    structure=structure,
                    direction=direction,
                )
                for setup_key_level in selected:
                    confirmations.extend(
                        self._confirmation.evaluate(
                            candles=data.m15,
                            structure=structure,
                            setup_key_level=setup_key_level,
                        )
                    )

            candidates = tuple(self._classifier.classify(tuple(confirmations)))
            if not candidates:
                return self._persist(
                    self._revision(
                        identity=identity,
                        revision_number=revision_number,
                        evaluation_timestamp=evaluated_at,
                        status=ObservationStatus.NO_SETUP,
                        reason=ObservationReason.NO_QUALIFYING_SETUP.value,
                        window=window,
                        data=data,
                        structure=structure,
                        key_levels=key_levels,
                    )
                )

            outcomes = []
            for candidate in candidates:
                risk_request = self._qualification.risk_request(
                    candidate=candidate,
                    key_levels=key_levels,
                    boundary=boundary,
                )
                risk_result = self._risk.assess(risk_request)

                governance_result = None
                if risk_result.status.value == "RISK_AUTHORIZED":
                    governance_request = self._qualification.governance_request(
                        candidate=candidate, boundary=boundary
                    )
                    governance_result = self._governance.authorize(
                        governance_request
                    )

                decision_result = self._decision.decide(
                    DecisionRequest(
                        candidate=candidate,
                        strategy_pending=False,
                        risk_result=risk_result,
                        governance_result=governance_result,
                    )
                )
                outcomes.append(
                    CandidateOutcome(
                        candidate=candidate,
                        risk_result=risk_result,
                        governance_result=governance_result,
                        decision_result=decision_result,
                    )
                )

            return self._persist(
                self._revision(
                    identity=identity,
                    revision_number=revision_number,
                    evaluation_timestamp=evaluated_at,
                    status=ObservationStatus.EVALUATED,
                    reason="EVALUATION_COMPLETED",
                    window=window,
                    data=data,
                    structure=structure,
                    key_levels=key_levels,
                    candidate_outcomes=tuple(outcomes),
                )
            )
        except ObservationExecutionError:
            raise
        except Exception as exc:
            raise ObservationExecutionError(
                f"MS-0.14 observation failed for {instrument} "
                f"at {boundary.isoformat()}: {exc}"
            ) from exc

    def _load_data(
        self, instrument: str, window: ObservationDataWindow
    ) -> "_DataBundle":
        h1 = tuple(
            self._market_data.get_candles(
                symbol=instrument,
                timeframe=Timeframe.H1,
                start=window.h1_start,
                end=window.h1_end,
            )
        )
        m15 = tuple(
            self._market_data.get_candles(
                symbol=instrument,
                timeframe=Timeframe.M15,
                start=window.m15_start,
                end=window.m15_end,
            )
        )
        quality = (
            (
                "H1",
                self._market_data.get_quality(
                    symbol=instrument,
                    timeframe=Timeframe.H1,
                    start=window.h1_start,
                    end=window.h1_end,
                ),
            ),
            (
                "M15",
                self._market_data.get_quality(
                    symbol=instrument,
                    timeframe=Timeframe.M15,
                    start=window.m15_start,
                    end=window.m15_end,
                ),
            ),
        )
        return _DataBundle(h1=h1, m15=m15, quality=quality)

    @staticmethod
    def _data_failure_reason(data: "_DataBundle") -> str | None:
        if any(
            not quality.valid or quality.rejected_records > 0
            for _, quality in data.quality
        ):
            return ObservationReason.INVALID_MARKET_DATA.value
        if any(not quality.sufficient for _, quality in data.quality):
            return ObservationReason.INSUFFICIENT_HISTORY.value
        if any(not quality.complete for _, quality in data.quality):
            return ObservationReason.INCOMPLETE_MARKET_DATA.value
        if not data.h1 or not data.m15:
            return ObservationReason.INSUFFICIENT_HISTORY.value
        return None

    @staticmethod
    def _directions_from_structure(structure) -> tuple[str, ...]:
        regime = structure.regime.value
        if regime == "UPTREND":
            return ("BUY",)
        if regime == "DOWNTREND":
            return ("SELL",)
        return ()

    def _revision(self, **kwargs) -> ObservationRevision:
        data = kwargs.pop("data")
        window = kwargs.pop("window")
        structure = kwargs.pop("structure", None)
        key_levels = kwargs.pop("key_levels", ())
        candidate_outcomes = kwargs.pop("candidate_outcomes", ())
        return ObservationRevision(
            **kwargs,
            methodology_versions=self._methodology_versions,
            data_window=window,
            market_structure=structure,
            key_levels=key_levels,
            candidate_outcomes=candidate_outcomes,
            h1_data_reference=_data_reference(data.h1),
            m15_data_reference=_data_reference(data.m15),
            validation_outcome=tuple(
                (name, "VALID" if quality.valid else "INVALID")
                for name, quality in data.quality
            ),
            provenance_refs=tuple(
                ref
                for _, quality in data.quality
                for ref in quality.provenance_refs
            ),
        )

    def _persist(self, revision: ObservationRevision) -> ObservationResult:
        try:
            result = self._repository.append(revision)
        except ObservationRevisionConflict:
            latest = self._repository.latest(revision.identity)
            if latest is None:
                raise
            return latest
        if self._audit is not None:
            self._audit.record(
                AuditRecord(
                    audit_id=(
                        f"OBS-{revision.identity.instrument}-"
                        f"{revision.identity.h1_boundary_timestamp.isoformat()}-"
                        f"{revision.revision_number}"
                    ),
                    timestamp=revision.evaluation_timestamp,
                    event_type="OBSERVATION_REVISION_PERSISTED",
                    strategy_version=MS014_VERSION,
                    decision_id=None,
                    payload_refs=revision.provenance_refs,
                    outcome=f"{revision.status.value}:{revision.reason}",
                )
            )
        return result

    @staticmethod
    def _utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            raise ValueError("observation timestamps must be timezone-aware")
        return value.astimezone(timezone.utc)


def _data_reference(candles: Sequence[MarketCandle]) -> str | None:
    if not candles:
        return None
    canonical = "|".join(
        f"{c.symbol},{c.timeframe.value},{c.timestamp_open.isoformat()},"
        f"{c.timestamp_close.isoformat()},{c.open},{c.high},{c.low},{c.close},{c.volume}"
        for c in candles
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


class _DataBundle:
    def __init__(
        self,
        *,
        h1: tuple[MarketCandle, ...],
        m15: tuple[MarketCandle, ...],
        quality: tuple[tuple[str, MarketDataQuality], ...],
    ) -> None:
        self.h1 = h1
        self.m15 = m15
        self.quality = quality
