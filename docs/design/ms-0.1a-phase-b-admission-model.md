# MS-0.1A Phase B — Design: Admission State Model

**Status:** Engineering design document. Not a specification amendment.
**Audience:** Phase B implementation (the VIOLATED/MISSING requirements from the fresh conformance audit).
**Spec authority:** `docs/strategy/ms-0.1a-market-structure-spec.md` as amended by 03, 04, 05, 06.
**Approved:** 2026-10-25.

## 1. Scope

This document defines the implementation approach for Phase B: the rework of the market-structure engine's meaningfulness, admission, classification-recording, and unresolved/excluded state. It does not change candidate detection, confirmation, opposing-swing handling, range boundary logic, or regime classification beyond the input they receive.

**Out of scope:**
- Candidate identification (§3) — unchanged.
- Confirmation (§4) — unchanged.
- Opposing-swing lifecycle including R13 rebinding — unchanged.
- RANGE boundary logic and breakout confirmation (§9) — unchanged.
- Regime classification structure (§7–§10) — unchanged in form; only the meaningful set fed into it changes.

**In scope (Phase B requirements):**

Group B (state model): R23, R24, R26, R30, R38, R40, R41, R42, R44, R46, R47, R48, R49, R51.

Group A (admission procedure): R15, R18, R19, R22, R29, R31, R32, R34, R45, R50, R57.

**Regression verification:** R56, R59, R65, R68.

## 2. What exists today

The current `_meaningful_swings()` admits every confirmed swing unconditionally. It emits `SWING_MEANINGFUL_PHASE1` for the first HIGH and first LOW, and `SWING_MEANINGFUL` for every subsequent confirmed swing. It performs no same-kind classification check, no opposite-kind consistency check, and no unresolved/excluded state tracking.

This is the central defect underlying all Group A and Group B requirements.

## 3. Conceptual model

The spec distinguishes three layers of information about a confirmed swing:

| Layer | What it records | Spec basis |
|---|---|---|
| Confirmation evidence | The swing was confirmed by a completed close beyond the opposing extreme | §4 |
| Classification | The swing's same-kind relationship (HH/LH/HL/LL/EQ) or CLASSIFICATION_UNRESOLVED | §6, amendment 05, amendment 06 |
| Admission | Whether the swing is in the active structural sequence, unresolved, or excluded | §5, §6, amendment 06 |

These are conceptually separate. A confirmed swing can be:

- Classified AND admitted (typical Phase 2 swing).
- CLASSIFICATION_UNRESOLVED AND admitted (Phase 1 bootstrap observation, per amendment 05).
- Classified AND unresolved (same-kind relationship known but opposite-kind evidence insufficient, per §6 + amendment 06 Section B).
- Classified AND excluded (same-kind and opposite-kind evidence both complete and demonstrably incompatible, per amendment 06 Section B).
- CLASSIFICATION_UNRESOLVED AND unresolved (both classification and admission deferred).
- CLASSIFICATION_UNRESOLVED AND excluded — not a valid combination per amendment 06 (exclusion requires determinable classification).

## 4. State representation

### 4.1 _Confirmed stays unchanged

`_Confirmed` remains a frozen record of confirmation evidence: `candidate` + `confirmed_at`. Adding admission or classification state to `_Confirmed` would conflate evidence with decisions and break immutability of confirmation records. The choice is architectural (evidence vs. decision), not just test convenience.

### 4.2 New types

The classification record is a public type, because it is exposed on MarketStructureState for downstream consumers and tests. It is immutable, self-contained, and has no reference to engine-internal types.

    @dataclass(frozen=True, slots=True)
    class ClassificationRecord:
        swing_timestamp: datetime
        swing_kind: SwingKind
        swing_price: Decimal
        classification: str | None  # "HH" / "LH" / "HL" / "LL" / "EQ_HIGH" / "EQ_LOW" / None
        reference_timestamp: datetime | None
        is_bootstrap: bool

The admission ledger and result are internal to the engine (private, not exposed on MarketStructureState). They are intermediate structures used by `_meaningful_swings` during evaluation. The engine projects their contents onto MarketStructureState for the public surface.

    @dataclass(frozen=True, slots=True)
    class _AdmissionLedger:
        admitted: tuple[_Confirmed, ...]
        unresolved: tuple[_Confirmed, ...]
        excluded: tuple[_Confirmed, ...]
        classification: dict[datetime, ClassificationRecord]
        episode_start: datetime | None

    @dataclass(frozen=True, slots=True)
    class _AdmissionResult:
        ledger: _AdmissionLedger
        events: tuple[str, ...]

### 4.3 Changes to MarketStructureState

Add three fields:

    excluded_swings: tuple[SwingPoint, ...]
        # confirmed swings excluded from the active sequence (Round 2)

    classification_records: tuple[ClassificationRecord, ...]
        # one record per confirmed swing, ordered by swing_timestamp (Round 1)

    confirmed_swings: tuple[SwingPoint, ...]
        # the confirmed swings themselves, ordered by timestamp (Round 1)

All existing fields preserved. These additions are backwards-compatible per §11 ("at minimum").

Round 1 populates `classification_records` and `confirmed_swings`; `excluded_swings` remains an empty tuple in Round 1 and is populated in Round 2.

## 5. _meaningful_swings signature and behavior

### 5.1 Signature

    def _meaningful_swings(
        self,
        confirmed: Sequence[_Confirmed],
        eligible: Sequence[MarketCandle],
        events: list[str],
    ) -> _AdmissionResult:

`eligible` is the candle list (needed to determine episode boundaries from prior invalidations). The method returns an `_AdmissionResult` containing the ledger and the events it produced. The caller (`evaluate`) extends its `events` list with `result.events`.

The engine's `evaluate()` method is the public surface. It calls `_meaningful_swings`, gets the `_AdmissionResult`, and projects the ledger's `classification` dict onto `MarketStructureState.classification_records` (as a sorted tuple of `ClassificationRecord`), and the confirmed swings onto `confirmed_swings`. The `_AdmissionLedger` and `_AdmissionResult` are engine-internal and not exposed on `MarketStructureState`.

### 5.2 Algorithm

Process `confirmed` in chronological order. For each swing:

1. Determine episode start. Compute the episode start as the last invalidation timestamp or None for the first episode. Swings before the episode start belong to a prior episode and are historical.

2. Check if the swing is a Phase 1 bootstrap. A swing is Phase 1 bootstrap if no prior admitted same-kind swing exists in the current episode and it is the first confirmed HIGH or first confirmed LOW of the episode. Per amendment 05 §A: such a swing is admitted with CLASSIFICATION_UNRESOLVED (permanent within episode).

3. Determine same-kind classification. Per §6 + amendment 06 Section A:
   - Find the most recent admitted same-kind swing in the current episode.
   - If found: classify as HH/LH/HL/LL/EQ_* by comparing prices/zones.
   - If not found: CLASSIFICATION_UNRESOLVED.

4. Determine admission.
   - Phase 1 bootstrap: admitted.
   - Else if same-kind classification is CLASSIFICATION_UNRESOLVED: unresolved.
   - Else: check opposite-kind structural consistency:
     - Complete and demonstrably incompatible evidence: excluded.
     - Insufficient or conflicting-but-not-incompatible evidence: unresolved.
     - Complete and consistent evidence: admitted.

5. Record the classification record: classification, reference_timestamp, is_bootstrap.

6. Emit the event per the event contract (§6).

### 5.3 Reconsideration (observation, not mechanism)

This document does not implement an explicit "reconsideration pass." Re-derivation is the reconsideration: each `evaluate()` call re-processes all confirmed swings with the current candles. An unresolved swing from evaluation N becomes admitted at N+1 if the additional candles provide the missing evidence.

Invariant 30's "one pass per admission/exclusion" is satisfied trivially: one pass = one `evaluate()` call. No recursive re-triggering exists because there is no inner loop.

## 6. Event contract

Final decisions per the design questions:

| Situation | Event |
|---|---|
| Confirmation (existing) | SWING_CONFIRMED:<ts> |
| Phase 1 bootstrap admission | SWING_MEANINGFUL_PHASE1:<ts> |
| Phase 2 classification successful + admitted | SWING_MEANINGFUL:<ts> |
| Phase 2 classification successful, still unresolved | SWING_CONFIRMED_UNRESOLVED:<ts>:conflict |
| Phase 1 bootstrap, forever unresolved | SWING_CONFIRMED_UNRESOLVED:<ts>:bootstrap |
| Swing excluded as non-extending | SWING_EXCLUDED:<ts>:non_extending_incompatible |
| Successful classification (intermediate) | (silent — no separate event) |

Event ordering: within a single `evaluate()` call, events are emitted in chronological order of the swing's timestamp_open, with the specific event per swing as decided above.

## 7. Transition table

The full transition table is in `docs/design/ms-0.1a-phase-b-transition-table.md`.

## 8. Implementation sequence

### 8.1 Round 1 — Foundation (Group B partial)

Files changed:
- src/trading_system/strategy/market_structure/engine.py (types + _meaningful_swings partial rewrite + _state signature)
- src/trading_system/domain/models.py (MarketStructureState.excluded_swings field)
- tests/unit/test_market_structure_engine.py (new tests for R40, R41, R22 partial)

Behavior: Phase 1 swings get CLASSIFICATION_UNRESOLVED. Non-bootstrap swings get classified against most recent admitted same-kind reference. Every classified swing is still admitted (no gate). No exclusions yet.

Tests target: R40, R41, plus partial-coverage tests for R22, R32. Baseline regressions from R56, R59, R65, R68 must still pass.

Expected full-suite count after Round 1: 326 + 3 = 329 passed.

### 8.2 Round 2 — Admission gate (Group A + Group B remaining)

Files changed:
- src/trading_system/strategy/market_structure/engine.py (admission gate + unresolved/excluded population + event emission)
- tests/unit/test_market_structure_engine.py (all remaining Phase B tests)

Behavior: Admission gate enforced. Swings classified but not admitted become unresolved or excluded. Unresolved/excluded excluded from meaningful_highs/meaningful_lows. Events emitted per §6.

Tests target: R15, R18, R19, R22, R23, R24, R26, R29, R30, R31, R32, R34, R38, R42, R44, R45, R46, R47, R48, R49, R50, R51, R57. Full regression on R56, R59, R65, R68.

Expected full-suite count after Round 2: 329 + 23 = 352 passed.

### 8.3 Regression verification (both rounds)

After each round:
- R56: test_r56_replacement_downtrend_established_after_uptrend_invalidation_is_not_transition must pass.
- R59: test_r59_no_range_breakout_recorded_while_trend_is_established must pass.
- R65: test_r65_range_penetration_is_decided_by_next_completed_candle must pass.
- R68: test_r68_established_uptrend_persists_after_close_above_last_swing_high must pass.

If any fails, the change has regressed prior work. Investigate before proceeding.

## 9. Phase B test list

The full test list is in `docs/design/ms-0.1a-phase-b-test-list.md`.

## 10. Regression plan

After Round 2, the following must still pass unchanged:
- All Phase A tests: R56, R59, R65, R68.
- All trend tests: T1–T6.
- All R13 tests.
- All prior baseline tests.

Any regression is a Phase B defect that must be addressed before the round completes.

## 11. Open items deferred to implementation

- Exact data structure for ClassificationRecord.classification — str | None or a small enum.
- Whether reference_timestamp should be a datetime or an index into confirmed.
- Whether to validate excluded_swings in MarketStructureState.__post_init__.
- Whether _meaningful_swings needs eligible at all or whether episode start can be derived from confirmed alone.

## 12. Revision history

- 2026-10-25: Initial draft, based on fresh conformance audit and Amendments 05/06.
- 2026-10-25: Finalized. Five design decisions accepted, two-round split approved.
- 2026-10-25: Amendment. ClassificationRecord promoted to public immutable dataclass. MarketStructureState extended with classification_records and confirmed_swings fields for testability and downstream consumers. _AdmissionLedger and _AdmissionResult explicitly remain engine-internal.