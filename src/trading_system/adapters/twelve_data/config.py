"""Configuration for the Twelve Data market-data adapter (MD-01, MD-03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from trading_system.domain import Timeframe


@dataclass(frozen=True, slots=True)
class TwelveDataAdapterConfig:
    """Runtime configuration for the Twelve Data adapter.

    All mappings and credentials are explicit. No fallback symbol guessing.
    """

    api_key: str
    symbol_map: Mapping[str, str]
    base_url: str = "https://api.twelvedata.com"
    timeout_seconds: float = 10.0
    poll_offset_seconds: int = 30
    warmup_start: str | None = None
    warmup_end: str | None = None

    def __post_init__(self) -> None:
        if not self.api_key:
            raise ValueError("api_key is required")
        if not self.symbol_map:
            raise ValueError("symbol_map must contain at least one mapping")
        required_canonical = {"EURUSD", "GBPUSD"}
        missing = required_canonical - set(self.symbol_map.keys())
        if missing:
            raise ValueError(f"missing required canonical symbols in symbol_map: {sorted(missing)}")
        for canonical, provider in self.symbol_map.items():
            if not provider:
                raise ValueError(f"provider symbol for {canonical} must not be empty")

    def get_provider_symbol(self, canonical: str) -> str:
        """Map canonical symbol to provider symbol.

        Raises KeyError if canonical symbol is not configured.
        """
        return self.symbol_map[canonical]

    def get_canonical_symbols(self) -> tuple[str, ...]:
        """Return the configured canonical symbols."""
        return tuple(self.symbol_map.keys())

    def get_timeframe_interval(self, timeframe: Timeframe) -> str:
        """Map Timeframe to Twelve Data interval string."""
        return {
            Timeframe.M15: "15min",
            Timeframe.H1: "1h",
        }[timeframe]

    def get_expected_duration_minutes(self, timeframe: Timeframe) -> int:
        """Return expected candle duration in minutes for completion boundary."""
        return {
            Timeframe.M15: 15,
            Timeframe.H1: 60,
        }[timeframe]