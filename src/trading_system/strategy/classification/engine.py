"""Deterministic MS-0.22 setup classification."""

from __future__ import annotations

from hashlib import sha256
from typing import Sequence

from trading_system.application.ports import SetupClassifierPort
from trading_system.domain import ConfirmationSequence, DecisionCandidate

CLASSIFICATION_VERSION = "MS-0.22"
_TRIGGERED = "SIGNAL_TRIGGERED"


class SetupClassifier(SetupClassifierPort):
    """Convert already-triggered confirmations into DecisionCandidates.

    This component carries forward confirmation semantics. It does not
    calculate stop loss, target, risk, governance, or execution behavior.
    """

    def classify(
        self, confirmations: Sequence[ConfirmationSequence]
    ) -> Sequence[DecisionCandidate]:
        candidates: list[DecisionCandidate] = []
        for confirmation in confirmations:
            if confirmation.signal_status != _TRIGGERED:
                continue
            if confirmation.signal_timestamp is None:
                raise ValueError("triggered confirmation requires signal_timestamp")
            if confirmation.signal_entry_price is None:
                raise ValueError("triggered confirmation requires signal_entry_price")
            if not confirmation.symbol:
                raise ValueError("triggered confirmation requires symbol")

            decision_id = _decision_id(confirmation)
            evidence_refs = (
                f"confirmation:{confirmation.setup_id}",
                f"key_level:{confirmation.setup_key_level}",
                *(f"candle:{ref}" for ref in confirmation.candle_refs),
                f"confirmation_type:{confirmation.confirmation_type.value}",
            )
            candidates.append(
                DecisionCandidate(
                    decision_id=decision_id,
                    strategy_version=CLASSIFICATION_VERSION,
                    symbol=confirmation.symbol,
                    direction=confirmation.direction,
                    setup_type=confirmation.confirmation_type,
                    setup_id=confirmation.setup_id,
                    signal_timestamp=confirmation.signal_timestamp,
                    signal_entry_price=confirmation.signal_entry_price,
                    proposed_stop_loss=None,
                    proposed_target=None,
                    evidence_refs=evidence_refs,
                )
            )
        return tuple(candidates)


def _decision_id(confirmation: ConfirmationSequence) -> str:
    canonical = "|".join(
        (
            CLASSIFICATION_VERSION,
            confirmation.symbol,
            confirmation.direction.value,
            confirmation.confirmation_type.value,
            confirmation.setup_id,
            confirmation.signal_timestamp.isoformat(),
            str(confirmation.signal_entry_price),
        )
    )
    return "DEC-" + sha256(canonical.encode("utf-8")).hexdigest()


__all__ = ["CLASSIFICATION_VERSION", "SetupClassifier"]
