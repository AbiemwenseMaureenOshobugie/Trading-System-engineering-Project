# MS-0.1A Phase B — Test List

**Status:** Companion to `ms-0.1a-phase-b-admission-model.md`.
**Purpose:** Enumerate every Phase B test, its target requirement, its expected baseline result (before implementation), and its expected result after implementation.

All tests target `tests/unit/test_market_structure_engine.py`.

## Round 1 tests (Group B foundation)

### T-R41 — Phase 1 swing classification unresolved

- **Test name:** `test_r41_phase1_swing_classification_unresolved`
- **Requirement:** R41 ("If no accepted meaningful same-kind reference exists, the engine records CLASSIFICATION_UNRESOLVED.")
- **Spec:** §6, Amendment 05 §A
- **Fixture:** Validated candle sequence producing exactly two confirmed swings: Phase 1 HIGH at hour 1, Phase 1 LOW at hour 7.
- **Assertions:**
  - `state.structural_events` contains `SWING_MEANINGFUL_PHASE1:<HIGH_ts>` and `SWING_MEANINGFUL_PHASE1:<LOW_ts>`
  - `state.structural_events` contains `SWING_CONFIRMED_UNRESOLVED:<HIGH_ts>:bootstrap` and `SWING_CONFIRMED_UNRESOLVED:<LOW_ts>:bootstrap`
- **Baseline (pre-Round-1):** FAILS — current engine emits only `SWING_MEANINGFUL_PHASE1`, no unresolved event.
- **Post-Round-1:** PASSES.

### T-R40 — Classification and reference recorded

- **Test name:** `test_r40_classification_and_reference_recorded`
- **Requirement:** R40 ("the engine records both the relationship classification and the exact reference swing used. That classification and reference are immutable.")
- **Spec:** §6, invariant 29
- **Fixture:** Construct `_Confirmed` objects directly via the `confirmed()` helper: two HIGHs where 2nd > 1st, two LOWs where 2nd > 1st. Call `_meaningful_swings` directly with `eligible=[]` (no invalidation).
- **Assertions:**
  - `result.ledger.classification` has a record for the second HIGH with `classification="HH"` and `reference_timestamp=<first_HIGH_ts>`
  - `result.ledger.classification` has a record for the second LOW with `classification="HL"` and `reference_timestamp=<first_LOW_ts>`
- **Baseline:** FAILS — `_meaningful_swings` currently returns `list[_Confirmed]`, not `_AdmissionResult`. Failure is `AttributeError: 'list' object has no attribute 'ledger'`.
- **Post-Round-1:** PASSES.

### T-R22-partial — Relationship determines participation (partial)

- **Test name:** `test_r22_relationship_determines_participation`
- **Requirement:** R22 ("structural relationships determine current active participation") — partial coverage.
- **Spec:** §5
- **Fixture:** Construct `_Confirmed` objects directly: Phase 1 HIGH, Phase 1 LOW, and subsequent swings of each kind. Call `_meaningful_swings` directly.
- **Assertions:**
  - Every non-bootstrap confirmed swing has a classification record with non-None classification
  - Bootstrap swings have `is_bootstrap=True` and `classification=None`
  - Classification is computed before any admission decision
- **Baseline:** FAILS — `_meaningful_swings` returns `list[_Confirmed]`, not `_AdmissionResult`.
- **Post-Round-1:** PASSES (partial).

## Round 2 tests (Group A + Group B remaining)

### T-R15 — Confirmation does not imply meaningfulness

- **Test name:** `test_r15_confirmation_does_not_imply_meaningfulness`
- **Requirement:** R15
- **Spec:** §4, §5, invariant 8
- **Fixture:** A confirmed swing that is classified but has conflicting opposite-kind evidence (unresolved, not admitted).
- **Assertions:**
  - `SWING_CONFIRMED:<ts>` emitted for the swing
  - Swing is NOT in `meaningful_highs`/`meaningful_lows`
  - Swing IS in `classification_records` with a non-None classification, and there is a `SWING_CONFIRMED_UNRESOLVED:<ts>:conflict` event
- **Baseline:** FAILS — current engine admits every confirmed swing.
- **Post-Round-2:** PASSES.

### T-R18 — Confirmation distinct from meaningfulness (structurally)

- **Test name:** `test_r18_confirmation_distinct_from_meaningfulness`
- **Requirement:** R18
- **Spec:** §5, invariant 8
- **Fixture:** Multiple confirmed swings where some are admitted and some are unresolved.
- **Assertions:**
  - Both admitted and unresolved swings appear in `confirmed_swings` and `structural_events` with confirmation events
  - Only admitted swings appear in `meaningful_highs`/`meaningful_lows`
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R19 — Admission requires active chain acceptance

- **Test name:** `test_r19_admission_requires_active_chain_acceptance`
- **Requirement:** R19
- **Spec:** §5
- **Fixture:** Confirmed swings that are classified but not consistent with active chain.
- **Assertions:**
  - Such swings are not in `meaningful_highs`/`meaningful_lows`
  - Their exclusion/unresolved status is observable in events
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R22-full — Full relationship gate

- **Test name:** extends `test_r22_relationship_determines_participation` from Round 1
- **Requirement:** R22 (full)
- **Fixture:** Same as partial + verify that classification result determines admission.
- **Assertions:** Classified swings with consistent opposite-kind evidence are admitted; with inconsistent evidence are not.
- **Post-Round-2:** Full assertion.

### T-R23 — Inactive swings auditable, not classifying

- **Test name:** `test_r23_inactive_swings_auditable_not_classifying`
- **Requirement:** R23
- **Spec:** §5
- **Fixture:** A sequence where an episode invalidates, then a new episode establishes.
- **Assertions:**
  - Prior-episode swings appear in `structural_events` (auditable)
  - Prior-episode swings do not appear in current `meaningful_highs`/`meaningful_lows`
  - Prior-episode swings are not used as references (test via `SWING_CONFIRMED_UNRESOLVED:bootstrap` for new episode)
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R24 — Excluded swing not reinstated

- **Test name:** `test_r24_excluded_swing_not_reinstated`
- **Requirement:** R24
- **Spec:** §5, invariant 31
- **Fixture:** A swing that meets exclusion criteria (complete, incompatible evidence). Then additional candles that would otherwise change context.
- **Assertions:**
  - Swing appears in `excluded_swings`
  - Swing is not in `meaningful_highs`/`meaningful_lows` across multiple evaluations
  - `SWING_EXCLUDED:<ts>:non_extending_incompatible` present in event log
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R26 — Unresolved distinct from excluded

- **Test name:** `test_r26_unresolved_distinct_from_excluded`
- **Requirement:** R26
- **Spec:** §5
- **Fixture:** Two swings: one with insufficient evidence (unresolved), one with incompatible evidence (excluded).
- **Assertions:**
  - Unresolved swing emits `SWING_CONFIRMED_UNRESOLVED:<ts>:conflict`
  - Excluded swing emits `SWING_EXCLUDED:<ts>:non_extending_incompatible`
  - Neither appears in `meaningful_highs`/`meaningful_lows`
  - Only excluded appears in `excluded_swings`
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R29 — Bootstrap reference not auto-meaningful

- **Test name:** `test_r29_bootstrap_reference_not_auto_meaningful`
- **Requirement:** R29
- **Spec:** §5 Phase 1
- **Fixture:** Phase 1 HIGH and LOW, then a second HIGH that has no valid opposite-kind evidence.
- **Assertions:**
  - Phase 1 swings are admitted with `CLASSIFICATION_UNRESOLVED`
  - Second HIGH is classified (using Phase 1 HIGH as reference) but is NOT auto-meaningful just because it has a reference
  - Second HIGH's admission depends on opposite-kind consistency
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R30 — Phase 2 gating

- **Test name:** `test_r30_phase2_gating`
- **Requirement:** R30
- **Spec:** §5 Phase 2, invariant 28
- **Fixture:** A sequence that reaches 2 HH + 2 HL. Then additional swings.
- **Assertions:**
  - Before 2 HH + 2 HL: no Phase 2 establishment event (or admitted swings accumulate)
  - After 2 HH + 2 HL: Phase 2 established
- **Baseline:** FAILS or PARTIAL.
- **Post-Round-2:** PASSES.

### T-R31 — No invented bootstrap

- **Test name:** `test_r31_phase1_no_invented_bootstrap`
- **Requirement:** R31
- **Spec:** §5
- **Fixture:** Phase 1 swings (must use Amendment 05's bootstrap rules, not invented rules).
- **Assertions:**
  - Phase 1 admission follows Amendment 05's rule (first HIGH and first LOW of episode)
  - No additional bootstrap rule (e.g., "first 3 swings" or "first 100 candles") is applied
- **Baseline:** FAILS or PARTIAL.
- **Post-Round-2:** PASSES.

### T-R32 — Active sequence excludes unresolved

- **Test name:** `test_r32_active_sequence_excludes_unresolved`
- **Requirement:** R32
- **Spec:** §5
- **Fixture:** Phase 1 HIGH, Phase 1 LOW, and a non-bootstrap swing that is unresolved (conflicting evidence).
- **Assertions:**
  - Phase 1 swings ARE in `meaningful_highs`/`meaningful_lows` (exception per Amendment 05)
  - Non-bootstrap unresolved swing is NOT in `meaningful_highs`/`meaningful_lows`
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R34 — Classification precedes admission

- **Test name:** `test_r34_classification_precedes_admission`
- **Requirement:** R34
- **Spec:** §6
- **Fixture:** Any multi-swing sequence.
- **Assertions:** For every admitted swing (except Phase 1), a classification record exists before it appears in `meaningful_highs`/`meaningful_lows`.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R38 — Excluded does not replace reference

- **Test name:** `test_r38_excluded_does_not_replace_reference`
- **Requirement:** R38
- **Spec:** §6, invariant 26
- **Fixture:** Phase 1 HIGH admitted as reference, then a second HIGH excluded. Then a third HIGH.
- **Assertions:**
  - Third HIGH's reference is the Phase 1 HIGH, not the excluded one
  - Classification of third HIGH is computed against Phase 1 HIGH
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R42 — Initial classification established later

- **Test name:** `test_r42_initial_classification_established_later`
- **Requirement:** R42
- **Spec:** §6, invariant 29
- **Fixture:** A swing that is CLASSIFICATION_UNRESOLVED at evaluation N (no reference), then at evaluation N+1 a reference exists.
- **Note:** Row 4 is rare; construct carefully or defer if impractical.
- **Assertions:** At N: classification None. At N+1: classification established.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES or DEFERRED (if fixture construction is impractical, note as deferred to a later round).

### T-R44 — Classification and participation separate

- **Test name:** `test_r44_classification_participation_separate`
- **Requirement:** R44
- **Spec:** §6
- **Fixture:** A swing that is classified (HH) but unresolved (insufficient opposite-kind evidence).
- **Assertions:**
  - Classification is available ("HH")
  - Swing is not admitted
  - These two facts are independently observable
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R45 — Unresolved not controlling

- **Test name:** `test_r45_unresolved_not_controlling`
- **Requirement:** R45
- **Spec:** §6
- **Fixture:** Established UPTREND with controlling HL. A subsequent HL swing is unresolved.
- **Assertions:**
  - Unresolved HL is not the controlling level
  - `controlling_level` remains the previously admitted controlling HL
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R46 — Unresolved event exposure

- **Test name:** `test_r46_swing_confirmed_unresolved_event`
- **Requirement:** R46
- **Spec:** §6
- **Fixture:** Same as T-R26.
- **Assertions:**
  - `SWING_CONFIRMED_UNRESOLVED:<ts>:conflict` present for unresolved
  - `SWING_CONFIRMED_UNRESOLVED:<ts>:bootstrap` present for Phase 1
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R47 — Unresolved excluded from meaningful

- **Test name:** `test_r47_unresolved_excluded_from_meaningful`
- **Requirement:** R47
- **Spec:** §6
- **Fixture:** Same as T-R26.
- **Assertions:** Unresolved swings are not in `meaningful_highs`/`meaningful_lows`.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R48 — Reconsideration bounded

- **Test name:** `test_r48_reconsideration_bounded`
- **Requirement:** R48
- **Spec:** §6, invariant 30
- **Fixture:** An unresolved swing, then multiple new confirmed swings in one evaluation.
- **Assertions:** No recursive or duplicate events; the unresolved swing's status is recomputed once per evaluation.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R49 — Classification established on reconsideration

- **Test name:** `test_r49_classification_established_on_reconsideration`
- **Requirement:** R49
- **Spec:** §6
- **Fixture:** A swing that was CLASSIFICATION_UNRESOLVED at N; reference becomes available at N+1.
- **Assertions:** Classification established at N+1. Once established, cannot be recalculated at N+2.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R50 — Admission gate

- **Test name:** `test_r50_admission_requires_consistent_evidence`
- **Requirement:** R50
- **Spec:** §6
- **Fixture:** Two swings with identical same-kind classification, one with consistent opposite-kind evidence, one with inconsistent.
- **Assertions:** Consistent one admitted, inconsistent one excluded/unresolved.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R51 — Excluded persists

- **Test name:** `test_r51_excluded_persists_no_reinstate`
- **Requirement:** R51
- **Spec:** §6, invariant 31
- **Fixture:** Same as T-R24.
- **Assertions:** After exclusion, subsequent evaluations do not re-admit the swing.
- **Baseline:** FAILS.
- **Post-Round-2:** PASSES.

### T-R57 — Invalidated non-controlling, episode-scoped

- **Test name:** `test_r57_invalidated_non_controlling_episode_scoped`
- **Requirement:** R57 (full)
- **Spec:** §8, Amendment 06 §C
- **Fixture:** UPTREND established, invalidated, then replacement episode with its own Phase 1 swings.
- **Assertions:**
  - `controlling_level = None` in TRANSITION
  - Replacement episode's first HIGH/LOW emit `SWING_CONFIRMED_UNRESOLVED:bootstrap` (prior swings not used as references)
  - Prior-episode swings do not appear in replacement episode's `meaningful_highs`/`meaningful_lows`
- **Baseline:** PARTIAL — `controlling_level = None` already implemented (from Phase A), but episode-scoped reference rules are not.
- **Post-Round-2:** PASSES (fully).

## Regression tests (must pass after each round)

These tests are existing and must not regress:

- `test_r56_replacement_downtrend_established_after_uptrend_invalidation_is_not_transition` (R56)
- `test_r59_no_range_breakout_recorded_while_trend_is_established` (R59)
- `test_r65_range_penetration_is_decided_by_next_completed_candle` (R65)
- `test_r68_established_uptrend_persists_after_close_above_last_swing_high` (R68)
- All T1–T6 trend tests
- `test_r13_opposing_swing_replacement_records_old_and_new_reference` (R13)
- All 326 baseline tests

## Test count summary

| Round | New tests | Full suite after |
|---|---|---|
| Baseline (pre-Round-1) | 0 | 326 |
| Round 1 | 3 | 329 |
| Round 2 | 23 | 352 |

If test counts differ at any point, investigate before proceeding.