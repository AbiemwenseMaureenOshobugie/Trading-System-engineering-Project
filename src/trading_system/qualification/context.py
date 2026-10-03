"""MS-0.23 qualification-context assembler."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Callable

from trading_system.application.ports import (
    AccountStatePort,
    ExecutionHistoryPort,
    InstrumentSpecificationPort,
    MarketExecutionContextPort,
    NoisePolicyPort,
    VolatilityPolicyPort,
)
from trading_system.domain import (
    DecisionCandidate,
    GovernanceRequest,
    KeyLevel,
    MarketStructureState,
    QualificationContextResult,
    RiskRequest,
)
from trading_system.domain.enums import QualificationContextStatus


class QualificationContextAssembler:
    """Assemble Risk/Governance inputs from authoritative qualification-time sources.

    Session eligibility is an explicit prerequisite. If no resolver is supplied,
    or it cannot provide a valid boolean at qualification time, the assembler
    fails closed. It never invents session hours or substitutes True/False.
    """

    VERSION = "MS-0.23"

    def __init__(
        self,
        *,
        account_state: AccountStatePort,
        market_execution_context: MarketExecutionContextPort,
        execution_history: ExecutionHistoryPort,
        noise_policy: NoisePolicyPort,
        volatility_policy: VolatilityPolicyPort,
        instrument_specification: InstrumentSpecificationPort,
        session_eligibility_resolver: Callable[[str, datetime], bool | None] | None = None,
    ) -> None:
        self._account_state = account_state
        self._market_execution_context = market_execution_context
        self._execution_history = execution_history
        self._noise_policy = noise_policy
        self._volatility_policy = volatility_policy
        self._instrument_specification = instrument_specification
        self._session_eligibility = session_eligibility_resolver

    def qualify(
        self,
        *,
        candidate: DecisionCandidate,
        key_levels: tuple[KeyLevel, ...] | list[KeyLevel],
        structure: MarketStructureState,
        boundary: datetime,
        qualification_timestamp: datetime,
    ) -> QualificationContextResult:
        if qualification_timestamp.tzinfo is None:
            raise ValueError("qualification_timestamp must be timezone-aware")

        session_eligible = self._resolve_session_eligibility(
            candidate.symbol, qualification_timestamp
        )
        if session_eligible is None:
            return self._unavailable(
                qualification_timestamp, "SESSION_ELIGIBILITY_UNAVAILABLE"
            )

        setup_key_level_id = self._setup_key_level_id(candidate)
        if setup_key_level_id is None:
            return self._unavailable(
                qualification_timestamp, "SETUP_KEY_LEVEL_REFERENCE_UNAVAILABLE"
            )

        if not any(
            level.key_level_id == setup_key_level_id and level.active
            for level in key_levels
        ):
            return self._unavailable(
                qualification_timestamp, "SETUP_KEY_LEVEL_UNAVAILABLE"
            )

        try:
            account_equity = self._account_state.get_account_equity(
                at=qualification_timestamp
            )
            spread = self._market_execution_context.get_spread(
                symbol=candidate.symbol, at=qualification_timestamp
            )
            slippage = self._execution_history.get_slippage(
                symbol=candidate.symbol, at=qualification_timestamp
            )
            daily_trade_count = self._execution_history.get_daily_trade_count(
                symbol=candidate.symbol, at=qualification_timestamp
            )
            daily_loss_count = self._execution_history.get_daily_loss_count(
                symbol=candidate.symbol, at=qualification_timestamp
            )
            noise = self._noise_policy.get_noise(
                candidate=candidate,
                structure=structure,
                at=qualification_timestamp,
            )
            volatility_adjustment = self._volatility_policy.get_volatility_adjustment(
                candidate=candidate, at=qualification_timestamp
            )
            value_per_price_unit = (
                self._instrument_specification.get_value_per_price_unit(
                    symbol=candidate.symbol, at=qualification_timestamp
                )
            )
        except Exception:
            return self._unavailable(
                qualification_timestamp, "QUALIFICATION_PROVIDER_UNAVAILABLE"
            )

        reason = self._validate_values(
            account_equity=account_equity,
            spread=spread,
            slippage=slippage,
            daily_trade_count=daily_trade_count,
            daily_loss_count=daily_loss_count,
            noise=noise,
            volatility_adjustment=volatility_adjustment,
            value_per_price_unit=value_per_price_unit,
        )
        if reason is not None:
            return self._unavailable(qualification_timestamp, reason)

        risk_request = RiskRequest(
            candidate=candidate,
            active_key_levels=tuple(key_levels),
            setup_key_level_id=setup_key_level_id,
            account_equity=account_equity,
            spread=spread,
            slippage=slippage,
            noise=noise,
            volatility_adjustment=volatility_adjustment,
            value_per_price_unit=value_per_price_unit,
        )
        governance_request = GovernanceRequest(
            candidate=candidate,
            instrument_session_eligible=session_eligible,
            daily_trade_count=daily_trade_count,
            daily_loss_count=daily_loss_count,
        )
        return QualificationContextResult(
            status=QualificationContextStatus.AVAILABLE,
            qualification_timestamp=qualification_timestamp,
            risk_request=risk_request,
            governance_request=governance_request,
            reason_codes=(),
        )

    def _resolve_session_eligibility(
        self, symbol: str, at: datetime
    ) -> bool | None:
        if self._session_eligibility is None:
            return None
        try:
            value = self._session_eligibility(symbol, at)
        except Exception:
            return None
        return value if isinstance(value, bool) else None

    @staticmethod
    def _setup_key_level_id(candidate: DecisionCandidate) -> str | None:
        refs = tuple(
            ref.removeprefix("key_level:")
            for ref in candidate.evidence_refs
            if ref.startswith("key_level:")
        )
        if len(refs) != 1 or not refs[0]:
            return None
        return refs[0]

    @staticmethod
    def _validate_values(
        *,
        account_equity: Decimal,
        spread: Decimal,
        slippage: Decimal,
        daily_trade_count: int,
        daily_loss_count: int,
        noise: Decimal,
        volatility_adjustment: Decimal,
        value_per_price_unit: Decimal,
    ) -> str | None:
        if not isinstance(account_equity, Decimal) or account_equity <= 0:
            return "INVALID_ACCOUNT_EQUITY"
        if not isinstance(spread, Decimal) or spread < 0:
            return "INVALID_SPREAD"
        if not isinstance(slippage, Decimal) or slippage < 0:
            return "INVALID_SLIPPAGE"
        if not isinstance(noise, Decimal) or noise < 0:
            return "INVALID_NOISE"
        if not isinstance(volatility_adjustment, Decimal) or volatility_adjustment < 0:
            return "INVALID_VOLATILITY_ADJUSTMENT"
        if (
            not isinstance(value_per_price_unit, Decimal)
            or value_per_price_unit <= 0
        ):
            return "INVALID_VALUE_PER_PRICE_UNIT"
        if not isinstance(daily_trade_count, int) or daily_trade_count < 0:
            return "INVALID_DAILY_TRADE_COUNT"
        if not isinstance(daily_loss_count, int) or daily_loss_count < 0:
            return "INVALID_DAILY_LOSS_COUNT"
        return None

    @staticmethod
    def _unavailable(timestamp: datetime, reason: str) -> QualificationContextResult:
        return QualificationContextResult(
            status=QualificationContextStatus.UNAVAILABLE,
            qualification_timestamp=timestamp,
            risk_request=None,
            governance_request=None,
            reason_codes=(reason,),
        )
