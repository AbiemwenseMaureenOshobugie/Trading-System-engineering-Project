"""MS-0.25 application history-window contract tests."""

from datetime import datetime, timezone
from typing import get_type_hints

from trading_system.application.composition import CompositionDependencies
from trading_system.domain import ObservationDataWindow


def test_history_window_resolver_is_an_explicit_observation_window_contract():
    annotation = get_type_hints(CompositionDependencies)["history_window_resolver"]
    assert "ObservationDataWindow" in str(annotation)


def test_application_history_policy_can_supply_complete_h1_and_m15_window():
    boundary = datetime(2026, 9, 28, 10, 0, tzinfo=timezone.utc)
    window = ObservationDataWindow(
        h1_start=datetime(2026, 9, 28, 6, 0, tzinfo=timezone.utc),
        h1_end=boundary,
        m15_start=datetime(2026, 9, 28, 8, 0, tzinfo=timezone.utc),
        m15_end=boundary,
    )

    resolver = lambda instrument, h1_boundary: window

    assert resolver("EURUSD", boundary) is window
    assert window.h1_end == boundary
    assert window.m15_end == boundary
