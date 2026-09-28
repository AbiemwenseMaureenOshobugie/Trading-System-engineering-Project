"""Canonical ASTER application composition root for MS-0.20."""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from trading_system.adapters.observation_sqlite import SQLiteObservationRepository
from trading_system.adapters.twelve_data.adapter import TwelveDataMarketDataAdapter
from trading_system.adapters.twelve_data.config import TwelveDataAdapterConfig
from trading_system.application.ports import (
    AuditPort,
    SetupClassifierPort,
)
from trading_system.decision import DecisionEngine
from trading_system.execution import ExecutionEngine
from trading_system.governance import GovernanceEngine
from trading_system.observation import (
    ExplicitObservationHistoryResolver,
    MarketDataH1BoundaryResolver,
    ObservationKeyLevelSelectorPort,
    ObservationQualificationContextPort,
    ObservationRunner,
    ObservationLifecycleCoordinator,
)
from trading_system.risk import RiskEngine
from trading_system.runtime import (
    FileRuntimeOwnership,
    RuntimeAuditPort,
    RuntimeConfig,
    RuntimeControl,
)
from trading_system.strategy.confirmation import M15ConfirmationEngine
from trading_system.strategy.key_levels import KeyLevelDetectionEngine
from trading_system.strategy.market_structure import H1MarketStructureEngine


class CompositionGapError(RuntimeError):
    """Raised when the frozen application graph cannot be completed safely."""


@dataclass(frozen=True, slots=True)
class CompositionDependencies:
    """Explicit application-level dependencies not yet implemented in production.

    This is a typed capability bundle, not a dependency-injection framework.
    """

    credential_resolver: Callable[[str], str]
    history_window_resolver: Callable[[str, datetime], object]
    key_level_selector: ObservationKeyLevelSelectorPort
    setup_classifier: SetupClassifierPort
    qualification_context: ObservationQualificationContextPort


class _AuditSink(AuditPort, RuntimeAuditPort):
    """Local-process audit sink used by the composition root."""

    def __init__(self) -> None:
        self.records: list[object] = []

    def record(self, event) -> None:
        self.records.append(event)


def compose_runtime(
    config: RuntimeConfig,
    *,
    dependencies: CompositionDependencies,
    clock: Callable[[], datetime] | None = None,
) -> RuntimeControl:
    """Construct the complete ASTER runtime dependency graph.

    This is the only authoritative application assembly operation.
    """

    if not config.instruments.instruments:
        raise CompositionGapError(("configured instrument universe is empty",))

    gaps = _validate_dependencies(dependencies)
    if gaps:
        raise CompositionGapError(gaps)

    now = clock or (lambda: datetime.now(timezone.utc))
    api_key = dependencies.credential_resolver(config.data_provider.credential_ref)
    if not api_key.strip():
        raise CompositionGapError(("market-data credential resolved to an empty value",))

    provider = config.data_provider.provider.strip().lower()
    if provider != "twelve_data":
        raise CompositionGapError(
            (f"unsupported configured market-data provider: {config.data_provider.provider}",)
        )

    market_data_config = TwelveDataAdapterConfig(
        api_key=api_key,
        symbol_map=dict(config.data_provider.symbol_mappings),
        base_url=config.data_provider.endpoint or "https://api.twelvedata.com",
    )
    market_data = TwelveDataMarketDataAdapter(config=market_data_config, clock=now)

    observation_repository = _build_repository(config)
    boundary = MarketDataH1BoundaryResolver(market_data)
    history = ExplicitObservationHistoryResolver(dependencies.history_window_resolver)
    structure = H1MarketStructureEngine()
    key_levels = KeyLevelDetectionEngine()
    confirmation = M15ConfirmationEngine()
    risk = RiskEngine()
    governance = GovernanceEngine()
    decision = DecisionEngine()

    audit = _AuditSink()
    execution = ExecutionEngine(audit_port=audit, clock=now)

    runner = ObservationRunner(
        market_data=market_data,
        boundary_port=boundary,
        history_resolver=history,
        structure_engine=structure,
        key_level_engine=key_levels,
        key_level_selector=dependencies.key_level_selector,
        confirmation_engine=confirmation,
        setup_classifier=dependencies.setup_classifier,
        risk_engine=risk,
        governance_engine=governance,
        decision_engine=decision,
        qualification_context=dependencies.qualification_context,
        repository=observation_repository,
        audit_port=audit,
        methodology_versions=(
            ("market_structure", "MS-0.1A"),
            ("key_levels", "MS-0.2"),
            ("confirmation", "MS-0.3"),
            ("risk", "MS-0.4"),
            ("governance", "MS-0.5"),
            ("decision", "MS-0.6"),
            ("execution", "MS-0.7"),
            ("observation", "MS-0.14"),
            ("observation_lifecycle", "MS-0.16"),
            ("runtime_control", "MS-0.17"),
            ("runtime_scheduler", "MS-0.18"),
            ("runtime_boundary", "MS-0.19"),
            ("application_composition", "MS-0.20"),
        ),
        clock=now,
    )

    coordinator = ObservationLifecycleCoordinator(
        clock=now,
        boundary_port=boundary,
        repository=observation_repository,
        runner=runner,
        poll_offset=config.operational_time.poll_offset,
    )

    ownership = FileRuntimeOwnership(
        runtime_id=config.runtime_id,
        lock_directory=_runtime_lock_directory(config),
    )

    return RuntimeControl(
        config=config,
        ownership=ownership,
        coordinator=coordinator,
        audit_port=audit,
        clock=now,
    )


def _validate_dependencies(
    dependencies: CompositionDependencies,
) -> tuple[str, ...]:
    missing: list[str] = []
    if dependencies.credential_resolver is None:
        missing.append("credential_resolution")
    if dependencies.history_window_resolver is None:
        missing.append("observation_history_policy")
    if dependencies.key_level_selector is None:
        missing.append("governing_key_level_selection")
    if dependencies.setup_classifier is None:
        missing.append("setup_classification")
    if dependencies.qualification_context is None:
        missing.append("risk_governance_qualification_context")
    return tuple(missing)


def _build_repository(config: RuntimeConfig):
    location = config.persistence.storage_location
    if location.startswith("sqlite://"):
        path = location.removeprefix("sqlite://")
        if not path:
            raise CompositionGapError(("SQLite persistence location is empty",))
        return SQLiteObservationRepository(path)
    raise CompositionGapError(
        (f"unsupported observation persistence location: {location}",)
    )


def _runtime_lock_directory(config: RuntimeConfig) -> Path:
    configured = os.environ.get("ASTER_RUNTIME_LOCK_DIR")
    if configured:
        return Path(configured)
    return Path(".aster") / "runtime-locks"
