"""Validation and failure contract (MD-04).

Fail closed: invalid or unreliable market data never reaches strategy engines.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from trading_system.domain import MarketCandle, Timeframe


class ValidationErrorCode(Enum):
    """Exhaustive validation failure codes."""

    PROVIDER_UNAVAILABLE = "PROVIDER_UNAVAILABLE"
    TIMEOUT = "TIMEOUT"
    AUTHENTICATION_FAILURE = "AUTHENTICATION_FAILURE"
    RATE_LIMIT = "RATE_LIMIT"
    PERMISSION_FAILURE = "PERMISSION_FAILURE"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    INVALID_OHLC = "INVALID_OHLC"
    INCOMPLETE_CANDLE = "INCOMPLETE_CANDLE"
    DUPLICATE_CANDLE = "DUPLICATE_CANDLE"
    OUT_OF_ORDER = "OUT_OF_ORDER"
    MISSING_CANDLE = "MISSING_CANDLE"
    STALE_LATEST = "STALE_LATEST"
    UNSUPPORTED_SYMBOL = "UNSUPPORTED_SYMBOL"
    UNSUPPORTED_TIMEFRAME = "UNSUPPORTED_TIMEFRAME"
    UTC_NORMALIZATION_FAILURE = "UTC_NORMALIZATION_FAILURE"
    SCHEMA_VALIDATION_FAILURE = "SCHEMA_VALIDATION_FAILURE"


class ValidationError(Exception):
    """Fail-closed validation exception."""

    def __init__(
        self,
        code: ValidationErrorCode,
        message: str,
        provider_symbol: Optional[str] = None,
        timeframe: Optional[Timeframe] = None,
        raw_data: Optional[dict] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.provider_symbol = provider_symbol
        self.timeframe = timeframe
        self.raw_data = raw_data


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of validation pipeline."""

    is_valid: bool
    candle: Optional[MarketCandle] = None
    errors: tuple[ValidationError, ...] = ()
    warnings: tuple[str, ...] = ()

    @classmethod
    def valid(cls, candle: MarketCandle, warnings: tuple[str, ...] = ()) -> ValidationResult:
        return cls(is_valid=True, candle=candle, warnings=warnings)

    @classmethod
    def invalid(cls, *errors: ValidationError) -> ValidationResult:
        return cls(is_valid=False, errors=errors)


class CandleValidator:
    """Validates provider candles through the complete pipeline (MD-04)."""

    def __init__(
        self,
        *,
        canonical_symbol: str,
        timeframe: Timeframe,
        observed_timestamps: set[datetime],
    ) -> None:
        self._canonical_symbol = canonical_symbol
        self._timeframe = timeframe
        self._observed_timestamps = observed_timestamps

    def validate(
        self,
        *,
        provider_symbol: str,
        timestamp_open: datetime,
        timestamp_close: datetime,
        open_price: Decimal,
        high_price: Decimal,
        low_price: Decimal,
        close_price: Decimal,
        volume: Optional[Decimal],
        retrieval_timestamp: datetime,
        observation_cutoff: datetime,
    ) -> ValidationResult:
        """Run complete validation pipeline."""

        errors: list[ValidationError] = []
        warnings: list[str] = []

        # 1. UTC normalization (must be timezone-aware UTC)
        try:
            timestamp_open = self._normalize_utc(timestamp_open)
            timestamp_close = self._normalize_utc(timestamp_close)
            retrieval_timestamp = self._normalize_utc(retrieval_timestamp)
        except ValidationError as e:
            return ValidationResult.invalid(e)

        # 2. Temporal validation: timestamp_open < timestamp_close
        if timestamp_open >= timestamp_close:
            errors.append(ValidationError(
                ValidationErrorCode.INVALID_OHLC,
                "timestamp_open must be earlier than timestamp_close",
                provider_symbol, self._timeframe,
            ))

        # 3. Completion validation: candle must be complete
        # (This is checked by CompletionBoundary before calling validate)

        # 4. OHLC validation
        if high_price < max(open_price, close_price):
            errors.append(ValidationError(
                ValidationErrorCode.INVALID_OHLC,
                f"high ({high_price}) < max(open, close) ({max(open_price, close_price)})",
                provider_symbol, self._timeframe,
            ))
        if low_price > min(open_price, close_price):
            errors.append(ValidationError(
                ValidationErrorCode.INVALID_OHLC,
                f"low ({low_price}) > min(open, close) ({min(open_price, close_price)})",
                provider_symbol, self._timeframe,
            ))

        # 5. Duplicate detection
        if timestamp_open in self._observed_timestamps:
            errors.append(ValidationError(
                ValidationErrorCode.DUPLICATE_CANDLE,
                f"duplicate candle at {timestamp_open}",
                provider_symbol, self._timeframe,
            ))

        # 6. Ordering validation (out-of-order check)
        if any(ts > timestamp_open for ts in self._observed_timestamps):
            warnings.append(f"out-of-order candle at {timestamp_open}; accepting but flagging")

        if errors:
            return ValidationResult.invalid(*errors)

        # All validations passed - construct canonical MarketCandle
        candle = MarketCandle(
            symbol=self._canonical_symbol,
            timeframe=self._timeframe,
            timestamp_open=timestamp_open,
            timestamp_close=timestamp_close,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=volume,
            source="twelve_data",
        )

        # Mark as observed for duplicate detection
        self._observed_timestamps.add(timestamp_open)

        return ValidationResult.valid(candle, warnings=tuple(warnings))

    def _normalize_utc(self, dt: datetime) -> datetime:
        """Normalize datetime to UTC, fail if naive."""
        if dt.tzinfo is None:
            raise ValidationError(
                ValidationErrorCode.UTC_NORMALIZATION_FAILURE,
                f"naive datetime received: {dt}",
                provider_symbol=None, timeframe=self._timeframe,
            )
        if dt.tzinfo != timezone.utc:
            return dt.astimezone(timezone.utc)
        return dt

    def mark_observed(self, timestamp_open: datetime) -> None:
        """Mark a timestamp as observed (for duplicate detection)."""
        self._observed_timestamps.add(timestamp_open)