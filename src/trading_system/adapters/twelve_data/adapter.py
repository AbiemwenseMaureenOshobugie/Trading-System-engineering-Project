"""Twelve Data market-data adapter implementing MarketDataPort (MD-01 through MD-06)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Mapping, Optional, Protocol, Sequence
from urllib import error, request

from trading_system.application.ports import MarketDataPort
from trading_system.domain import MarketCandle, Timeframe

from .completion import CompletionBoundary, CompletionResult
from .config import TwelveDataAdapterConfig
from .mapper import SymbolMapper
from .polling import PollingConfig, PollingSchedule
from .provenance import IngestionBatch, IngestionOutcome, IngestionRecord
from .validation import CandleValidator, ValidationError, ValidationErrorCode, ValidationResult


class TwelveDataAdapterError(Exception):
    """Base exception for Twelve Data adapter failures."""

    def __init__(self, message: str, code: Optional[str] = None) -> None:
        super().__init__(message)
        self.code = code


class TwelveDataGateway(Protocol):
    """Protocol for HTTP gateway (allows fake HTTP client in tests)."""

    def get(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, Any]: ...


class RealTwelveDataGateway:
    """Real HTTP gateway for Twelve Data REST API."""

    def __init__(self, base_url: str, api_key: str, timeout: float) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout

    def get(self, url: str, params: Mapping[str, str], timeout: float) -> Mapping[str, Any]:
        full_url = f"{self._base_url}{url}"
        query = "&".join(f"{k}={request.quote(str(v))}" for k, v in params.items())
        req_url = f"{full_url}?{query}"
        req = request.Request(req_url, headers={"Accept": "application/json"})
        try:
            with request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except error.HTTPError as e:
            body = e.read().decode("utf-8") if e.fp else ""
            raise TwelveDataAdapterError(
                f"HTTP {e.code}: {body}", code=f"HTTP_{e.code}"
            ) from e
        except error.URLError as e:
            raise TwelveDataAdapterError(f"Network error: {e.reason}", code="NETWORK_ERROR") from e
        except json.JSONDecodeError as e:
            raise TwelveDataAdapterError(f"Invalid JSON response: {e}", code="MALFORMED_RESPONSE") from e


@dataclass(frozen=True, slots=True)
class IngestionCycleResult:
    """Result of a single ingestion cycle."""

    candles: tuple[MarketCandle, ...]
    ingestion_batch: IngestionBatch
    latest_timestamp: Optional[datetime]


class TwelveDataMarketDataAdapter:
    """Twelve Data market data adapter implementing MarketDataPort."""

    VERSION = "MS-0.13"
    PROVIDER_NAME = "twelve_data"

    def __init__(
        self,
        *,
        config: TwelveDataAdapterConfig,
        gateway: Optional[TwelveDataGateway] = None,
        clock=None,
    ) -> None:
        self._config = config
        self._gateway = gateway or RealTwelveDataGateway(
            config.base_url, config.api_key, config.timeout_seconds
        )
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._mapper = SymbolMapper.from_config(config.symbol_map)
        self._polling = PollingSchedule(config.poll_offset_seconds)
        self._polling_config = PollingConfig(config.poll_offset_seconds)
        self._observed_timestamps: dict[tuple[str, Timeframe], set[datetime]] = {}

    def verify_entitlement(self) -> None:
        """Verify entitlement for all configured symbols (MD-01 safeguard).

        Must be called before observation runner starts.
        Raises TwelveDataAdapterError if any symbol is not accessible.
        """
        for canonical in self._mapper.canonical_symbols():
            provider = self._mapper.to_provider(canonical)
            self._check_symbol_access(provider)

    def _check_symbol_access(self, provider_symbol: str) -> None:
        """Check if a provider symbol is accessible."""
        try:
            params = {
                "symbol": provider_symbol,
                "interval": "15min",
                "outputsize": 1,
                "apikey": self._config.api_key,
            }
            data = self._gateway.get("/time_series", params, self._config.timeout_seconds)
            if data.get("status") == "error":
                raise TwelveDataAdapterError(
                    f"Entitlement check failed for {provider_symbol}: {data.get('message', 'unknown')}",
                    code="ENTITLEMENT_FAILURE",
                )
        except TwelveDataAdapterError:
            raise
        except Exception as e:
            raise TwelveDataAdapterError(
                f"Entitlement check error for {provider_symbol}: {e}",
                code="ENTITLEMENT_ERROR",
            ) from e

    def get_candles(
        self,
        *,
        symbol: str,
        timeframe: Timeframe,
        start: datetime,
        end: datetime,
    ) -> Sequence[MarketCandle]:
        """Fetch completed candles for the given range (MarketDataPort).

        This method implements the full validation pipeline (MD-04).
        Only complete, validated candles are returned.
        """
        if symbol not in self._mapper.canonical_symbols():
            raise TwelveDataAdapterError(
                f"unsupported canonical symbol: {symbol}",
                code="UNSUPPORTED_SYMBOL",
            )

        provider_symbol = self._mapper.to_provider(symbol)
        interval = self._config.get_timeframe_interval(timeframe)

        # Normalize timestamps to UTC
        start = self._normalize_utc(start)
        end = self._normalize_utc(end)

        # Calculate outputsize (max candles to request)
        # Twelve Data max outputsize is 5000
        duration_minutes = self._config.get_expected_duration_minutes(timeframe)
        max_candles = max(1, int((end - start).total_seconds() / 60 / duration_minutes) + 1)
        outputsize = min(max_candles, 5000)

        params = {
            "symbol": provider_symbol,
            "interval": interval,
            "outputsize": str(outputsize),
            "timezone": "UTC",
            "apikey": self._config.api_key,
        }

        cycle_start = self._clock()
        observation_cutoff = cycle_start

        try:
            raw_data = self._gateway.get("/time_series", params, self._config.timeout_seconds)
        except TwelveDataAdapterError as e:
            ingestion_record = IngestionRecord(
                provider=self.PROVIDER_NAME,
                provider_symbol=provider_symbol,
                canonical_symbol=symbol,
                timeframe=timeframe,
                retrieval_timestamp=cycle_start,
                observation_cutoff=observation_cutoff,
                request_context={"interval": interval, "outputsize": outputsize, "start": start.isoformat(), "end": end.isoformat()},
                validation_outcome=self._map_error_to_outcome(e),
                candles_accepted=0,
                candles_rejected=0,
                candles_withheld_incomplete=0,
                error_details=str(e),
            )
            return ()

        if raw_data.get("status") == "error":
            msg = raw_data.get("message", "unknown error")
            if "rate limit" in msg.lower() or "quota" in msg.lower():
                outcome = IngestionOutcome.RATE_LIMIT
            elif "auth" in msg.lower() or "apikey" in msg.lower():
                outcome = IngestionOutcome.AUTHENTICATION_FAILURE
            elif "permission" in msg.lower() or "entitle" in msg.lower():
                outcome = IngestionOutcome.PERMISSION_FAILURE
            else:
                outcome = IngestionOutcome.MALFORMED_RESPONSE
            ingestion_record = IngestionRecord(
                provider=self.PROVIDER_NAME,
                provider_symbol=provider_symbol,
                canonical_symbol=symbol,
                timeframe=timeframe,
                retrieval_timestamp=cycle_start,
                observation_cutoff=observation_cutoff,
                request_context={"interval": interval, "outputsize": outputsize, "start": start.isoformat(), "end": end.isoformat()},
                validation_outcome=outcome,
                candles_accepted=0,
                candles_rejected=0,
                candles_withheld_incomplete=0,
                error_details=msg,
            )
            return ()

        # Parse and validate candles
        values = raw_data.get("values", [])
        if not values:
            ingestion_record = IngestionRecord(
                provider=self.PROVIDER_NAME,
                provider_symbol=provider_symbol,
                canonical_symbol=symbol,
                timeframe=timeframe,
                retrieval_timestamp=cycle_start,
                observation_cutoff=observation_cutoff,
                request_context={"interval": interval, "outputsize": outputsize, "start": start.isoformat(), "end": end.isoformat()},
                validation_outcome=IngestionOutcome.NO_NEW_CANDLES,
                candles_accepted=0,
                candles_rejected=0,
                candles_withheld_incomplete=0,
            )
            return ()

        # Initialize observed timestamps for this symbol/timeframe
        key = (symbol, timeframe)
        if key not in self._observed_timestamps:
            self._observed_timestamps[key] = set()

        validator = CandleValidator(
            canonical_symbol=symbol,
            timeframe=timeframe,
            observed_timestamps=self._observed_timestamps[key],
        )

        boundary = CompletionBoundary.from_cutoff(observation_cutoff)
        accepted: list[MarketCandle] = []
        rejected = 0
        withheld = 0

        for item in values:
            try:
                ts_open = datetime.fromisoformat(item["datetime"].replace("Z", "+00:00"))
                if ts_open.tzinfo is None:
                    ts_open = ts_open.replace(tzinfo=timezone.utc)
            except (KeyError, ValueError) as e:
                rejected += 1
                continue

            # Check completion boundary (MD-02)
            completion = boundary.is_complete(ts_open, timeframe)
            if completion is CompletionResult.INCOMPLETE:
                withheld += 1
                continue
            if completion is CompletionResult.INVALID_TIMESTAMP:
                rejected += 1
                continue

            # Parse OHLC
            try:
                o = Decimal(str(item["open"]))
                h = Decimal(str(item["high"]))
                l = Decimal(str(item["low"]))
                c = Decimal(str(item["close"]))
                v = Decimal(str(item["volume"])) if "volume" in item and item["volume"] else None
            except (KeyError, ValueError) as e:
                rejected += 1
                continue

            # Calculate expected close
            ts_close = boundary.expected_close(ts_open, timeframe)

            # Validate through pipeline (MD-04)
            result = validator.validate(
                provider_symbol=provider_symbol,
                timestamp_open=ts_open,
                timestamp_close=ts_close,
                open_price=o,
                high_price=h,
                low_price=l,
                close_price=c,
                volume=v,
                retrieval_timestamp=cycle_start,
                observation_cutoff=observation_cutoff,
            )

            if result.is_valid and result.candle:
                accepted.append(result.candle)
                validator.mark_observed(ts_open)
            else:
                rejected += 1

        # Filter to requested range
        accepted = [c for c in accepted if start <= c.timestamp_open < end]

        cycle_end = self._clock()
        ingestion_record = IngestionRecord(
            provider=self.PROVIDER_NAME,
            provider_symbol=provider_symbol,
            canonical_symbol=symbol,
            timeframe=timeframe,
            retrieval_timestamp=cycle_start,
            observation_cutoff=observation_cutoff,
            request_context={"interval": interval, "outputsize": outputsize, "start": start.isoformat(), "end": end.isoformat()},
            validation_outcome=IngestionOutcome.SUCCESS,
            candles_accepted=len(accepted),
            candles_rejected=rejected,
            candles_withheld_incomplete=withheld,
        )

        return tuple(accepted)

    def ingestion_cycle(
        self,
        *,
        timeframe: Timeframe,
        lookback_candles: int = 100,
    ) -> IngestionCycleResult:
        """Run a single ingestion cycle for all configured symbols (for observation runner).

        This is the boundary-driven polling entry point (MD-05).
        """
        cycle_start = self._clock()
        observation_cutoff = cycle_start

        all_candles: list[MarketCandle] = []
        records: list[IngestionRecord] = []
        latest_ts: Optional[datetime] = None

        for canonical in self._mapper.canonical_symbols():
            provider_symbol = self._mapper.to_provider(canonical)
            interval = self._config.get_timeframe_interval(timeframe)

            # Calculate lookback period
            duration_minutes = self._config.get_expected_duration_minutes(timeframe)
            start = observation_cutoff - timedelta(minutes=duration_minutes * lookback_candles)

            params = {
                "symbol": provider_symbol,
                "interval": interval,
                "outputsize": str(min(lookback_candles + 10, 5000)),
                "timezone": "UTC",
                "apikey": self._config.api_key,
            }

            try:
                raw_data = self._gateway.get("/time_series", params, self._config.timeout_seconds)
            except TwelveDataAdapterError as e:
                records.append(IngestionRecord(
                    provider=self.PROVIDER_NAME,
                    provider_symbol=provider_symbol,
                    canonical_symbol=canonical,
                    timeframe=timeframe,
                    retrieval_timestamp=cycle_start,
                    observation_cutoff=observation_cutoff,
                    request_context={"interval": interval, "start": start.isoformat()},
                    validation_outcome=self._map_error_to_outcome(e),
                    candles_accepted=0,
                    candles_rejected=0,
                    candles_withheld_incomplete=0,
                    error_details=str(e),
                ))
                continue

            if raw_data.get("status") == "error":
                msg = raw_data.get("message", "unknown error")
                if "rate limit" in msg.lower() or "quota" in msg.lower():
                    outcome = IngestionOutcome.RATE_LIMIT
                elif "auth" in msg.lower() or "apikey" in msg.lower():
                    outcome = IngestionOutcome.AUTHENTICATION_FAILURE
                elif "permission" in msg.lower() or "entitle" in msg.lower():
                    outcome = IngestionOutcome.PERMISSION_FAILURE
                else:
                    outcome = IngestionOutcome.MALFORMED_RESPONSE
                records.append(IngestionRecord(
                    provider=self.PROVIDER_NAME,
                    provider_symbol=provider_symbol,
                    canonical_symbol=canonical,
                    timeframe=timeframe,
                    retrieval_timestamp=cycle_start,
                    observation_cutoff=observation_cutoff,
                    request_context={"interval": interval, "start": start.isoformat()},
                    validation_outcome=outcome,
                    candles_accepted=0,
                    candles_rejected=0,
                    candles_withheld_incomplete=0,
                    error_details=msg,
                ))
                continue

            values = raw_data.get("values", [])
            if not values:
                records.append(IngestionRecord(
                    provider=self.PROVIDER_NAME,
                    provider_symbol=provider_symbol,
                    canonical_symbol=canonical,
                    timeframe=timeframe,
                    retrieval_timestamp=cycle_start,
                    observation_cutoff=observation_cutoff,
                    request_context={"interval": interval, "start": start.isoformat()},
                    validation_outcome=IngestionOutcome.NO_NEW_CANDLES,
                    candles_accepted=0,
                    candles_rejected=0,
                    candles_withheld_incomplete=0,
                ))
                continue

            key = (canonical, timeframe)
            if key not in self._observed_timestamps:
                self._observed_timestamps[key] = set()

            validator = CandleValidator(
                canonical_symbol=canonical,
                timeframe=timeframe,
                observed_timestamps=self._observed_timestamps[key],
            )

            boundary = CompletionBoundary.from_cutoff(observation_cutoff)
            accepted_count = 0
            rejected_count = 0
            withheld_count = 0

            for item in values:
                try:
                    ts_open = datetime.fromisoformat(item["datetime"].replace("Z", "+00:00"))
                    if ts_open.tzinfo is None:
                        ts_open = ts_open.replace(tzinfo=timezone.utc)
                except (KeyError, ValueError):
                    rejected_count += 1
                    continue

                completion = boundary.is_complete(ts_open, timeframe)
                if completion is CompletionResult.INCOMPLETE:
                    withheld_count += 1
                    continue
                if completion is CompletionResult.INVALID_TIMESTAMP:
                    rejected_count += 1
                    continue

                try:
                    o = Decimal(str(item["open"]))
                    h = Decimal(str(item["high"]))
                    l = Decimal(str(item["low"]))
                    c = Decimal(str(item["close"]))
                    v = Decimal(str(item["volume"])) if "volume" in item and item["volume"] else None
                except (KeyError, ValueError):
                    rejected_count += 1
                    continue

                ts_close = boundary.expected_close(ts_open, timeframe)

                result = validator.validate(
                    provider_symbol=provider_symbol,
                    timestamp_open=ts_open,
                    timestamp_close=ts_close,
                    open_price=o,
                    high_price=h,
                    low_price=l,
                    close_price=c,
                    volume=v,
                    retrieval_timestamp=cycle_start,
                    observation_cutoff=observation_cutoff,
                )

                if result.is_valid and result.candle:
                    all_candles.append(result.candle)
                    if latest_ts is None or result.candle.timestamp_open > latest_ts:
                        latest_ts = result.candle.timestamp_open
                    accepted_count += 1
                    validator.mark_observed(ts_open)
                else:
                    rejected_count += 1

            records.append(IngestionRecord(
                provider=self.PROVIDER_NAME,
                provider_symbol=provider_symbol,
                canonical_symbol=canonical,
                timeframe=timeframe,
                retrieval_timestamp=cycle_start,
                observation_cutoff=observation_cutoff,
                request_context={"interval": interval, "start": start.isoformat()},
                validation_outcome=IngestionOutcome.SUCCESS,
                candles_accepted=accepted_count,
                candles_rejected=rejected_count,
                candles_withheld_incomplete=withheld_count,
            ))

        cycle_id = f"ingest-{timeframe.value}-{cycle_start.strftime('%Y%m%d%H%M%S')}"
        batch = IngestionBatch(
            cycle_id=cycle_id,
            start_time=cycle_start,
            end_time=self._clock(),
            records=tuple(records),
        )

        # Sort by timestamp
        all_candles.sort(key=lambda c: c.timestamp_open)

        return IngestionCycleResult(
            candles=tuple(all_candles),
            ingestion_batch=batch,
            latest_timestamp=latest_ts,
        )

    def _normalize_utc(self, dt: datetime) -> datetime:
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        if dt.tzinfo != timezone.utc:
            return dt.astimezone(timezone.utc)
        return dt

    def _map_error_to_outcome(self, e: TwelveDataAdapterError) -> IngestionOutcome:
        if e.code in ("NETWORK_ERROR", "TIMEOUT"):
            return IngestionOutcome.TIMEOUT
        if e.code in ("HTTP_401", "HTTP_403", "ENTITLEMENT_FAILURE", "ENTITLEMENT_ERROR"):
            return IngestionOutcome.AUTHENTICATION_FAILURE
        if e.code == "HTTP_429":
            return IngestionOutcome.RATE_LIMIT
        if e.code == "MALFORMED_RESPONSE":
            return IngestionOutcome.MALFORMED_RESPONSE
        return IngestionOutcome.PROVIDER_UNAVAILABLE