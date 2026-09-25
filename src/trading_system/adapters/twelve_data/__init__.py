"""Twelve Data market-data adapter package for MS-0.13."""

from .adapter import TwelveDataMarketDataAdapter
from .config import TwelveDataAdapterConfig
from .completion import CompletionBoundary, CompletionResult
from .mapper import SymbolMapper, CanonicalSymbol, ProviderSymbol
from .polling import PollingSchedule
from .provenance import IngestionRecord, IngestionOutcome
from .validation import CandleValidator, ValidationError, ValidationErrorCode, ValidationResult

__all__ = [
    "TwelveDataMarketDataAdapter",
    "TwelveDataAdapterConfig",
    "CompletionBoundary",
    "CompletionResult",
    "SymbolMapper",
    "CanonicalSymbol",
    "ProviderSymbol",
    "PollingSchedule",
    "IngestionRecord",
    "IngestionOutcome",
    "CandleValidator",
    "ValidationError",
    "ValidationErrorCode",
    "ValidationResult",
]