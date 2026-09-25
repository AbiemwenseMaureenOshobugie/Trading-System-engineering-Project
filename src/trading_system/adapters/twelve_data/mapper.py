"""Symbol mapping between canonical ASTER symbols and Twelve Data provider symbols (MD-03)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping


CanonicalSymbol = str
ProviderSymbol = str


@dataclass(frozen=True, slots=True)
class SymbolMapper:
    """Adapter-owned symbol mapping.

    - Canonical universe: EURUSD, GBPUSD
    - Provider format: EUR/USD, GBP/USD
    - Mappings live in adapter configuration
    - Provider identifiers never leak into strategy code
    - No fallback symbol guessing
    """

    _canonical_to_provider: Mapping[CanonicalSymbol, ProviderSymbol]
    _provider_to_canonical: Mapping[ProviderSymbol, CanonicalSymbol]

    @classmethod
    def from_config(cls, symbol_map: Mapping[CanonicalSymbol, ProviderSymbol]) -> SymbolMapper:
        """Create mapper from configuration symbol_map."""
        if not symbol_map:
            raise ValueError("symbol_map must not be empty")
        for canonical, provider in symbol_map.items():
            if not provider:
                raise ValueError(f"provider symbol for {canonical} must not be empty")
        provider_to_canonical = {v: k for k, v in symbol_map.items()}
        if len(provider_to_canonical) != len(symbol_map):
            raise ValueError("symbol_map contains duplicate provider symbols")
        return cls(
            _canonical_to_provider=symbol_map,
            _provider_to_canonical=provider_to_canonical,
        )

    def to_provider(self, canonical: CanonicalSymbol) -> ProviderSymbol:
        """Map canonical symbol to provider symbol.

        Raises KeyError if canonical symbol is not configured.
        """
        try:
            return self._canonical_to_provider[canonical]
        except KeyError as exc:
            raise KeyError(f"no provider mapping for canonical symbol: {canonical}") from exc

    def to_canonical(self, provider: ProviderSymbol) -> CanonicalSymbol:
        """Map provider symbol to canonical symbol.

        Raises KeyError if provider symbol is not recognized.
        """
        try:
            return self._provider_to_canonical[provider]
        except KeyError as exc:
            raise KeyError(f"unrecognized provider symbol: {provider}") from exc

    def canonical_symbols(self) -> tuple[CanonicalSymbol, ...]:
        """Return all configured canonical symbols."""
        return tuple(self._canonical_to_provider.keys())

    def provider_symbols(self) -> tuple[ProviderSymbol, ...]:
        """Return all configured provider symbols."""
        return tuple(self._canonical_to_provider.values())

    def is_supported(self, canonical: CanonicalSymbol) -> bool:
        """Check if canonical symbol is supported."""
        return canonical in self._canonical_to_provider