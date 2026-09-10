"""Integration smoke test for the package layout."""


def test_strategy_subpackages_exist() -> None:
    from trading_system.strategy import confirmation, key_levels, market_structure

    assert confirmation is not None
    assert key_levels is not None
    assert market_structure is not None
