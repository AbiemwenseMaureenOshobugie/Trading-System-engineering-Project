"""MS-0.20 application-composition tests."""

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from trading_system.application.composition import (
    CompositionDependencies,
    CompositionGapError,
    compose_runtime,
)
from trading_system.domain import (
    ConfirmationType,
    DecisionCandidate,
    GovernanceRequest,
    QualificationContextResult,
    QualificationContextStatus,
    KeyLevel,
    MarketCandle,
    ObservationDataWindow,
    RiskRequest,
    Timeframe,
)
from trading_system.runtime import (
    DataProviderConfig,
    InstrumentConfig,
    OperationalTimeConfig,
    PersistenceConfig,
    RuntimeConfig,
)


UTC = timezone.utc
NOW = datetime(2026, 9, 28, 10, 0, tzinfo=UTC)


class Classifier:
    def classify(self, confirmations):
        return ()


class Qualification:
    def qualify(
        self,
        *,
        candidate,
        key_levels,
        structure,
        boundary,
        qualification_timestamp,
    ):
        return QualificationContextResult(
            status=QualificationContextStatus.AVAILABLE,
            qualification_timestamp=qualification_timestamp,
            risk_request=RiskRequest(
                candidate=candidate,
                active_key_levels=tuple(key_levels),
                setup_key_level_id=None,
                account_equity=Decimal("10000"),
                spread=Decimal("0"),
                slippage=Decimal("0"),
                noise=Decimal("0"),
                volatility_adjustment=Decimal("0"),
                value_per_price_unit=Decimal("100000"),
            ),
            governance_request=GovernanceRequest(
                candidate=candidate,
                instrument_session_eligible=True,
                daily_trade_count=0,
                daily_loss_count=0,
            ),
            reason_codes=(),
        )


def config(tmp_path):
    return RuntimeConfig(
        runtime_id="ms020-test",
        instruments=InstrumentConfig(("EURUSD",)),
        operational_time=OperationalTimeConfig(),
        data_provider=DataProviderConfig(
            provider="twelve_data",
            credential_ref="env:TEST_TWELVE_DATA_KEY",
            symbol_mappings=(("EURUSD", "EUR/USD"), ("GBPUSD", "GBP/USD")),
        ),
        persistence=PersistenceConfig(
            repository_ref="sqlite-observation",
            storage_location=f"sqlite://{tmp_path / 'observations.sqlite3'}",
        ),
    )


def dependencies():
    return CompositionDependencies(
        credential_resolver=lambda reference: "test-key",
        history_window_resolver=lambda instrument, boundary: ObservationDataWindow(
            h1_start=boundary.replace(hour=boundary.hour - 4),
            h1_end=boundary,
            m15_start=boundary.replace(hour=boundary.hour - 2),
            m15_end=boundary,
        ),
        qualification_context=Qualification(),
    )


class Classifier:
    def classify(self, confirmations):
        return ()


class Qualification:
    def risk_request(self, *, candidate, key_levels, boundary):
        return RiskRequest(
            candidate=candidate,
            active_key_levels=tuple(key_levels),
            setup_key_level_id=None,
            account_equity=Decimal("10000"),
            spread=Decimal("0"),
            slippage=Decimal("0"),
            noise=Decimal("0"),
            volatility_adjustment=Decimal("0"),
            value_per_price_unit=Decimal("100000"),
        )

    def governance_request(self, *, candidate, boundary):
        return GovernanceRequest(
            candidate=candidate,
            instrument_session_eligible=True,
            daily_trade_count=0,
            daily_loss_count=0,
        )


def test_composition_fails_closed_without_unresolved_capabilities(tmp_path):
    with pytest.raises(CompositionGapError):
        compose_runtime(
            config(tmp_path),
            dependencies=CompositionDependencies(
                credential_resolver=None,
                history_window_resolver=None,
                qualification_context=None,
            ),
            clock=lambda: NOW,
        )


def test_composition_returns_wired_runtime_control(tmp_path):
    runtime = compose_runtime(
        config(tmp_path),
        dependencies=dependencies(),
        clock=lambda: NOW,
    )

    assert runtime.runtime_id == "ms020-test"
    assert runtime.status.value == "STOPPED"
    assert runtime._coordinator._runner._structure.__class__.__name__ == "H1MarketStructureEngine"
    assert runtime._coordinator._runner._key_levels.__class__.__name__ == "KeyLevelDetectionEngine"
    assert runtime._coordinator._runner._confirmation.__class__.__name__ == "M15ConfirmationEngine"
    assert runtime._coordinator._runner._risk.__class__.__name__ == "RiskEngine"
    assert runtime._coordinator._runner._governance.__class__.__name__ == "GovernanceEngine"
    assert runtime._coordinator._runner._decision.__class__.__name__ == "DecisionEngine"


def test_composition_does_not_start_runtime(tmp_path):
    runtime = compose_runtime(
        config(tmp_path),
        dependencies=dependencies(),
        clock=lambda: NOW,
    )
    assert runtime.status.value == "STOPPED"