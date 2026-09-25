"""External system adapters."""

from .mt5 import (
    MT5AdapterConfig,
    MT5AdapterError,
    MT5ConnectionState,
    MT5ExecutionAdapter,
    MetaTrader5Gateway,
)
from .twelve_data import (
    TwelveDataAdapterConfig,
    TwelveDataMarketDataAdapter,
    CompletionBoundary,
    CompletionResult,
    SymbolMapper,
    CanonicalSymbol,
    ProviderSymbol,
    PollingSchedule,
    IngestionRecord,
    IngestionOutcome,
    CandleValidator,
    ValidationError,
    ValidationErrorCode,
    ValidationResult,
)

__all__ = [
    "MT5AdapterConfig",
    "MT5AdapterError",
    "MT5ConnectionState",
    "MT5ExecutionAdapter",
    "MetaTrader5Gateway",
    "TwelveDataAdapterConfig",
    "TwelveDataMarketDataAdapter",
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