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

Classification labels are typed via an enum, so invalid values cannot be represented:

    class SwingClassification(Enum):
        HH = "HH"
        LH = "LH"
        HL = "HL"
        LL = "LL"
        EQ_HIGH = "EQ_HIGH"
        EQ_LOW = "EQ_LOW"

    @dataclass(frozen=True, slots=True)
    class ClassificationRecord:
        swing_timestamp: datetime
        swing_kind: SwingKind
        swing_price: Decimal
        classification: SwingClassification | None  # None only for Phase 1 bootstrap
        reference_timestamp: datetime | None
        is_bootstrap: bool

The admission ledger and result are internal to the engine (private, not exposed on MarketStructureState). They are intermediate structures used by `_meaningful_swings` during evaluation. The engine projects their contents onto MarketStructureState for the public surface.

    @dataclass(frozen=True, slots=True)
    class _AdmissionLedger:
        admitted: tuple[_Confirmed, ...]
        unresolved: tuple[_Confirmed, ...]
        excluded: tuple[_Confirmed, ...]
        classification: tuple[ClassificationRecord, ...]  # immutable; ordered by swing_timestamp
        episode_start: datetime | None

    @dataclass(frozen=True, slots=True)
    class _AdmissionResult:
        ledger: _AdmissionLedger
        events: tuple[str, ...]

### 4.3 Changes to MarketStructureState

Round 1 adds two fields:

    classification_records: tuple[ClassificationRecord, ...]
        # one record per confirmed swing, ordered by swing_timestamp

    confirmed_swings: tuple[SwingPoint, ...]
        # the confirmed swings themselves, ordered by timestamp

Round 2 adds one more field:

    excluded_swings: tuple[SwingPoint, ...]
        # confirmed swings excluded from the active sequence

All existing fields preserved. These additions are backwards-compatible per §11 ("at minimum").

A field is added only when the corresponding behavior is implemented. `excluded_swings` is deferred to Round 2 because Round 1 produces no exclusions. Adding a field that is permanently empty in Round 1 would imply functionality the milestone does not yet provide.

## 5. _meaningful_swings signature and behavior

### 5.1 Signature

Round 1 signature:

    def _meaningful_swings(
        self,
        confirmed: Sequence[_Confirmed],
    ) -> _AdmissionResult:

The method returns an `_AdmissionResult` containing the ledger and the events it produced. The caller (`evaluate`) extends its `events` list with `result.events`.

Round 2 extends the signature to include episode-boundary inputs (e.g., `eligible: Sequence[MarketCandle]`) when multi-episode semantics are implemented. Round 1 does not include unused parameters.

The engine's `evaluate()` method is the public surface. It calls `_meaningful_swings`, gets the `_AdmissionResult`, and projects the ledger's `classification` tuple onto `MarketStructureState.classification_records`, and the confirmed swings onto `confirmed_swings`. The `_AdmissionLedger` and `_AdmissionResult` are engine-internal and not exposed on `MarketStructureState`.

### 5.2 Algorithm

Process `confirmed` in chronological order. For each swing:

1. Determine episode start. In Round 1, episode start is always None (single-episode assumption): the entire `confirmed` set is treated as the first episode. Multi-episode handling — deriving episode start from prior invalidations in `eligible` — is deferred to Round 2. Round 1's behavior must not be interpreted as correct for fixtures that include an invalidation; those fixtures are Round 2 scope.

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

### 5.3 Reconsideration (episode-local, explicit pass)

**Supersedes the Round 2A wording.** The Round 2A text stated that "this document does not implement an explicit 'reconsideration pass'" and that re-derivation happens "on the next `evaluate()` call" with "no inner loop." That wording is retired. It described a whole-history calculation model and is incompatible with Amendment 08 §D (same-close ordering) and §F7 (per-episode reconsideration).

Amendment 08 §D requires that the invalidation decision at a completed-candle close uses the episode-local structural state available strictly *before* that close. Any unresolved swing whose admission outcome would change given the state at that close must be reconsidered *before* the close is processed, not deferred to the next `evaluate()` call. The "no inner loop" reading cannot satisfy that requirement.

Reconsideration is therefore redefined as:

- An **episode-local, explicit pass** owned by `_replay` (§5.4).
- **Triggered** by `_admit_one` returning `reconsideration_trigger = True`, or by admission of a new swing into an episode that already contains unresolved swings (the evidence base changes).
- **Executed before** the episode is closed or a replacement is initialized.
- **Audited**: the ledger records each reconsideration pass, the swings re-evaluated, and their outcomes.

Canonical asymmetry preserved: unresolved swings may be reconsidered; excluded swings are never reinstated (MS-0.1A canonical specification, Amendment 08 §F4–§F5).

### 5.4 `_replay` and `_admit_one` contract

Amendment 08 §D requires chronological replay in which the invalidation decision at each close uses only pre-close episode state, and Amendment 08 §F requires per-episode admission independence. The Round 2A implementation folded admission into one inline loop inside `_meaningful_swings()` with no separation between single-swing evaluation, episode-state mutation, and the decision to reconsider. That structure cannot satisfy the ordering requirement because the reconsideration decision and the invalidation decision share state.

Round 2B splits the admission path into two methods.

**`_admit_one` — single-swing evaluator.**

- Evaluates one confirmed swing against the supplied episode state.
- Returns an explicit outcome: `admitted`, `unresolved`, or `excluded`.
- Returns the supporting-swing selection, if any.
- Returns a boolean `reconsideration_trigger` indicating whether the outcome should cause `_replay` to run another pass.
- Does **not** mutate episode collections.
- Does **not** run another pass itself.
- Does **not** perform same-close historical assignment (Amendment 08 §D4); that is `_replay`'s responsibility.

**`_replay` — episode state owner.**

- Owns the episode-local `admitted`, `unresolved`, and `excluded` collections.
- Owns the current episode's `episode_start` boundary.
- Owns the same-close processing order and episode transitions per Amendment 08 §D.
- Calls `_admit_one` for each confirmed swing in `confirmed_at` order.
- Applies the returned outcome.
- Decides whether a reconsideration pass is required, using `_admit_one`'s `reconsideration_trigger` and the arrival of new confirmed evidence into an episode containing unresolved swings.
- Distinguishes **historical same-close assignment** from **active admission**: a swing confirmed at an invalidation close is recorded in the closing episode's ledger as assigned-at-close (audit-only) and is not added to either episode's admitted collection, per Amendment 08 §D4 and §D5.

`_AdmissionLedger.episode_start` is a real boundary for every episode that has admitted at least one swing. The Round 2A value `episode_start=None` for all episodes is retired by Round 2B.

The `_AdmissionLedger` gains one field:

```python
assigned_at_close: tuple[_Confirmed, ...]
    # swings confirmed at the invalidation close, assigned to the
    # closing episode as audit-only; never members of either episode

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
- src/trading_system/strategy/market_structure/engine.py (types + _meaningful_swings partial rewrite + _state signature + evaluate wiring)
- src/trading_system/domain/models.py (SwingClassification enum, ClassificationRecord, MarketStructureState fields)
- tests/unit/test_market_structure_engine.py (new tests for R40, R41, R22 partial)

Behavior: Phase 1 swings get CLASSIFICATION_UNRESOLVED (bootstrap). Non-bootstrap swings get classified against the most recent admitted same-kind reference. Every classified swing is still admitted (no admission gate). No exclusions in Round 1.

**Milestone constraint:** Round 1 implements single-episode semantics only. Episode start is always None. Multi-episode handling (per-episode Phase 1 bootstrap after invalidation) is deferred to Round 2. This is a scope boundary, not a claim that multi-episode behavior is currently correct.

Tests target:
- R41 — exact bootstrap records for the confirmed HIGH and LOW (typed as `is_bootstrap=True, classification=None`).
- R40 — typed classifications (`SwingClassification.HH` / `.HL`) and reference timestamps for the second HIGH and second LOW.
- R22 — explicitly named `test_r22_partial_classification_records_present`, verifying that classification records exist for non-bootstrap swings. This is a partial test; the full R22 invariant (structural relationships determine admission) requires Round 2's admission gate.

Baseline regressions from R56, R59, R65, R68 must still pass.

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

## Round 2A known defect — confirmation timestamp ordering

**Recorded:** 2026-11-01.
**Status:** Known defect, to be corrected in Round 2B under Amendment 08.

The Round 2A implementation does not consistently use `confirmed_at` when ordering confirmed swings and determining episode membership.

Specifically:

- `_meaningful_swings()` sorts confirmed swings using `swing.timestamp`, which is the originating middle candle's opening timestamp.
- `_classify()` filters episode membership using `swing.timestamp` rather than `confirmed_at`.

This does not conform to Amendment 07 §F3, which defines episode membership using the confirmation timestamp, and it is the defect that Amendment 08 §E makes explicit.

The defect was not detected by the Round 2A test suite because the existing fixtures use the `confirmed()` helper, which produces swings where `timestamp_open` and `confirmed_at` are separated by exactly one hour (the confirmation candle's close). For all Round 2A fixtures, the two orderings coincide, so the defect is invisible.

**Disposition:** Known defect to be corrected in Round 2B under Amendment 08.

Round 2B shall:

1. Correct `_meaningful_swings` and `_classify` to use `confirmed_at` for ordering, admission, classification, and episode membership.
2. Add test R2B-16: a fixture where `timestamp_open` ordering differs from `confirmed_at` ordering; admission and classification must follow `confirmed_at`.
3. Verify that all Round 2A tests still pass after the correction. Because Round 2A fixtures have coincident orderings, all Round 2A tests should pass unchanged. Any Round 2A test that fails after the correction indicates either a Round 2A fixture that accidentally encoded the defect or a genuine Round 2B implementation issue, and shall be investigated rather than accommodated.

Round 2A's reported test result (`340 passed, 1 skipped` at commit `b959d0c`) remains valid as a test result. It does not establish full conformance with the confirmation-time ordering requirement of Amendment 07 §F3.

## Round 2B design decisions — Amendment 08 conformance

**Recorded:** 2026-11-26.
**Status:** Frozen design contract for Round 2B implementation.
**Authority:** MS-0.1A canonical specification, Amendments 07 and 08.
**Implementation gate:** Engine changes must not merge until they conform to §5.3, §5.4, and this section.

The Round 2B audit established that Amendment 08 is merged as documentation but not implemented. `main` at the time of the audit carried the Round 2A engine, the Round 2A test suite, and this design document with the Round 2A reconsideration wording. Three findings:

1. Same-close processing order not implemented (Finding 1). Addressed by §5.3 (reconsideration) and §5.4 (`_replay` / `_admit_one`), plus the fixture list below.
2. `_replay` / `_admit_one` not implemented (Finding 2). Addressed by §5.4.
3. `_Confirmed` / `confirmed_at` not preserved throughout the internal path (Finding 3). The design defect is already recorded in the 2026-11-01 entry above and is not repeated here. Round 2B implements the fix; the entry above remains the authoritative description of the defect.

### Same-close assignment vs. active admission

Amendment 08 §D4 states that same-close confirmed swings are assigned to the episode ending at the invalidation close. Amendment 08 §D5 states they shall not become active references in the replacement episode. The design must express both halves explicitly:

- **Historical same-close assignment** is an audit-only record in the closing episode's ledger, in a dedicated `assigned_at_close` field (§5.4).
- **Active admission** is membership in an episode's `admitted` collection, entitling the swing to serve as a same-kind reference, opposite-kind supporting evidence, or regime-establishment evidence.

A swing confirmed at an invalidation close is assigned, not admitted, to the closing episode. It is not admitted into the replacement. It does not influence replacement structure, bootstrap, same-kind references, or opposite-kind supporting evidence. It does not appear in either episode's `admitted` collection.

### Round 2B fixtures required

The fixture set must include, and each fixture must demonstrate the defect it is designed to expose against the pre-Round-2B engine:

- Valid UPTREND invalidation sequence.
- Valid DOWNTREND invalidation sequence.
- Wick-only non-invalidation variant.
- Same-close confirmation and invalidation case (exercises §D4 / §D5 split).
- Swing confirmed after an episode boundary despite originating before it (exercises §E2–§E3).
- Divergent `timestamp_open` and `confirmed_at` ordering (R2B-16, per 2026-11-01 entry).
- Replacement-episode bootstrap and independent regime establishment (exercises §F1–§F3).
- Repeated invalidation (exercises §G).
- Reconsidered-admitted: unresolved swing reconsidered and admitted within-episode (exercises §5.3).
- Unresolved-at-close: unresolved swing remains unresolved when its episode closes, recorded as such in the ledger (exercises §5.3 and §10).
- Excluded-not-reinstated: excluded swing is not reinstated despite later evidence (exercises §5.3 canonical asymmetry).

A fixture that passes on the pre-Round-2B engine is rejected unless its purpose is a regression guard, and that purpose is recorded in the fixture itself.

### Open item from §11 closed

§11 listed "Whether `_meaningful_swings` needs `eligible` at all or whether episode start can be derived from `confirmed` alone." Round 2B closes this: per Amendment 08 §C5, the invalidation decision at each close uses pre-close episode state, which cannot be derived from the confirmed-swing list alone. Episode boundaries are produced by the chronological candle replay. `_replay` therefore requires the eligible candle sequence as input, not only the confirmed swings.

### Round 2B deliverables

1. `_replay` implemented as episode state owner (§5.4).
2. `_admit_one` implemented as single-swing evaluator (§5.4).
3. `_Confirmed` retained internally; `confirmed_at` used for all chronological decisions throughout the internal path (2026-11-01 entry).
4. Round 2B test suite covering every requirement in this section and the fixtures above.
5. Round 2A regression suite passing unchanged. Any Round 2A test that fails after the correction is investigated, not accommodated (2026-11-01 entry).

### Out of scope for Round 2B

- Candidate identification (§3 of the MS-0.1A canonical specification).
- Confirmation rules (§4).
- Opposing-swing lifecycle including R13 rebinding.
- RANGE boundary logic.
- Regime classification structure.

These remain unchanged by Round 2B.

## 12. Revision history

- 2026-10-25: Initial draft, based on fresh conformance audit and Amendments 05/06.
- 2026-10-25: Finalized. Five design decisions accepted, two-round split approved.
- 2026-10-25: Amendment. ClassificationRecord promoted to public immutable dataclass. MarketStructureState extended with classification_records and confirmed_swings fields for testability and downstream consumers. _AdmissionLedger and _AdmissionResult explicitly remain engine-internal.
- 2026-10-26: Amendment 02. Immutable ledger (classification as tuple, not dict). SwingClassification enum for typed labels. excluded_swings deferred to Round 2. Round 1 restricted to single-episode semantics. _meaningful_swings signature for Round 1 is `(confirmed)` without unused parameters. R22 test renamed to reflect partial scope.
- 2026-11-01: Recorded Round 2A confirmed_at ordering defect, to be corrected in Round 2B under Amendment 08.
- 2026-11-26: Round 2B design freeze. §5.3 superseded (reconsideration is episode-local, explicit pass owned by `_replay`; old "next `evaluate()` call, no inner loop" wording retired). §5.4 added (`_replay` / `_admit_one` split). Round 2B section appended: same-close assignment is audit-only per Amendment 08 §D4–§D5, not active admission; fixture list named; §11 open item closed. Round 2A `confirmed_at` defect entry (2026-11-01) unchanged.
