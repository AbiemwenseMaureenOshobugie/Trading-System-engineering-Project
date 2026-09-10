"""Smoke tests for the initial package structure."""

from importlib import import_module


def test_top_level_package_imports() -> None:
    package = import_module("trading_system")
    assert package.__version__ == "0.1.0"


def test_architecture_packages_import() -> None:
    packages = (
        "domain",
        "data",
        "features",
        "strategy",
        "risk",
        "governance",
        "decision",
        "execution",
        "audit",
        "analytics",
        "explanation",
        "adapters",
    )
    for name in packages:
        import_module(f"trading_system.{name}")
