\# MS-0.1A Phase B — Test List



\*\*Status:\*\* Companion to `ms-0.1a-phase-b-admission-model.md`.

\*\*Purpose:\*\* Enumerate every Phase B test, its target requirement, its expected baseline result (before implementation), and its expected result after implementation.



All tests target `tests/unit/test\_market\_structure\_engine.py`.



\## Round 1 tests (Group B foundation)



\### T-R41 — Phase 1 swing classification unresolved



\- \*\*Test name:\*\* `test\_r41\_phase1\_swing\_classification\_unresolved`

\- \*\*Requirement:\*\* R41 ("If no accepted meaningful same-kind reference exists, the engine records CLASSIFICATION\_UNRESOLVED.")

\- \*\*Spec:\*\* §6, Amendment 05 §A

\- \*\*Fixture:\*\* A sequence with one confirmed HIGH and one confirmed LOW, no prior swings. Evaluate with cutoff after both.

\- \*\*Assertions:\*\*

&#x20; - `state.structural\_events` contains `SWING\_MEANINGFUL\_PHASE1:<HIGH\_ts>` and `SWING\_MEANINGFUL\_PHASE1:<LOW\_ts>`

&#x20; - `state.structural\_events` contains `SWING\_CONFIRMED\_UNRESOLVED:<HIGH\_ts>:bootstrap` and `SWING\_CONFIRMED\_UNRESOLVED:<LOW\_ts>:bootstrap`

&#x20; - Classification record for both swings has `classification=None, is\_bootstrap=True`

\- \*\*Baseline (pre-Round-1):\*\* FAILS — current engine emits only `SWING\_MEANINGFUL\_PHASE1`, no `CLASSIFICATION\_UNRESOLVED` state.

\- \*\*Post-Round-1:\*\* PASSES.



\### T-R40 — Classification and reference recorded



\- \*\*Test name:\*\* `test\_r40\_classification\_and\_reference\_recorded`

\- \*\*Requirement:\*\* R40 ("the engine records both the relationship classification and the exact reference swing used. That classification and reference are immutable.")

\- \*\*Spec:\*\* §6, invariant 29

\- \*\*Fixture:\*\* A sequence with confirmed HIGHs and LOWs such that a second HIGH is classifiable against the first (HH), and a second LOW is classifiable against the first (HL).

\- \*\*Assertions:\*\*

&#x20; - Classification record for the second HIGH has `classification="HH", reference\_timestamp=<first\_HIGH\_ts>`

&#x20; - Classification record for the second LOW has `classification="HL", reference\_timestamp=<first\_LOW\_ts>`

&#x20; - Re-evaluation with identical inputs yields identical records

\- \*\*Baseline:\*\* FAILS — no classification record exists.

\- \*\*Post-Round-1:\*\* PASSES.



\### T-R22-partial — Relationship determines participation (partial)



\- \*\*Test name:\*\* `test\_r22\_relationship\_determines\_participation`

\- \*\*Requirement:\*\* R22 ("structural relationships determine current active participation") — partial coverage.

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* A sequence with a Phase 1 HIGH, Phase 1 LOW, and subsequent swings of each kind. Ensure classifications are established.

\- \*\*Assertions:\*\*

&#x20; - All Phase 2 swings have classification available in the ledger

&#x20; - Classification is computed before any admission decision

&#x20; - (Round 2 adds full assertion that admission depends on classification)

\- \*\*Baseline:\*\* FAILS — no classification ledger.

\- \*\*Post-Round-1:\*\* PASSES (partial).

\- \*\*Post-Round-2:\*\* Full assertion added.



\## Round 2 tests (Group A + Group B remaining)



\### T-R15 — Confirmation does not imply meaningfulness



\- \*\*Test name:\*\* `test\_r15\_confirmation\_does\_not\_imply\_meaningfulness`

\- \*\*Requirement:\*\* R15

\- \*\*Spec:\*\* §4, §5, invariant 8

\- \*\*Fixture:\*\* A confirmed swing that is classified but has conflicting opposite-kind evidence (unresolved, not admitted).

\- \*\*Assertions:\*\*

&#x20; - `SWING\_CONFIRMED:<ts>` emitted for the swing

&#x20; - Swing is NOT in `meaningful\_highs`/`meaningful\_lows`

&#x20; - Swing IS in some unresolved representation (e.g., `SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict` event)

\- \*\*Baseline:\*\* FAILS — current engine admits every confirmed swing.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R18 — Confirmation distinct from meaningfulness (structurally)



\- \*\*Test name:\*\* `test\_r18\_confirmation\_distinct\_from\_meaningfulness`

\- \*\*Requirement:\*\* R18

\- \*\*Spec:\*\* §5, invariant 8

\- \*\*Fixture:\*\* Multiple confirmed swings where some are admitted and some are unresolved.

\- \*\*Assertions:\*\*

&#x20; - Both admitted and unresolved swings appear in `structural\_events` with confirmation events

&#x20; - Only admitted swings appear in `meaningful\_highs`/`meaningful\_lows`

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R19 — Admission requires active chain acceptance



\- \*\*Test name:\*\* `test\_r19\_admission\_requires\_active\_chain\_acceptance`

\- \*\*Requirement:\*\* R19

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* Confirmed swings that are classified but not consistent with active chain.

\- \*\*Assertions:\*\*

&#x20; - Such swings are not in `meaningful\_highs`/`meaningful\_lows`

&#x20; - Their exclusion/unresolved status is observable in events

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R22-full — Full relationship gate



\- \*\*Test name:\*\* extends `test\_r22\_relationship\_determines\_participation` from Round 1

\- \*\*Requirement:\*\* R22 (full)

\- \*\*Fixture:\*\* Same as partial + verify that classification result determines admission.

\- \*\*Assertions:\*\* Classified swings with consistent opposite-kind evidence are admitted; with inconsistent evidence are not.

\- \*\*Post-Round-2:\*\* Full assertion.



\### T-R23 — Inactive swings auditable, not classifying



\- \*\*Test name:\*\* `test\_r23\_inactive\_swings\_auditable\_not\_classifying`

\- \*\*Requirement:\*\* R23

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* A sequence where an episode invalidates, then a new episode establishes.

\- \*\*Assertions:\*\*

&#x20; - Prior-episode swings appear in `structural\_events` (auditable)

&#x20; - Prior-episode swings do not appear in current `meaningful\_highs`/`meaningful\_lows`

&#x20; - Prior-episode swings are not used as references (test via `SWING\_CONFIRMED\_UNRESOLVED:bootstrap` for new episode)

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R24 — Excluded swing not reinstated



\- \*\*Test name:\*\* `test\_r24\_excluded\_swing\_not\_reinstated`

\- \*\*Requirement:\*\* R24

\- \*\*Spec:\*\* §5, invariant 31

\- \*\*Fixture:\*\* A swing that meets exclusion criteria (complete, incompatible evidence). Then additional candles that would otherwise change context.

\- \*\*Assertions:\*\*

&#x20; - Swing appears in `excluded\_swings`

&#x20; - Swing is not in `meaningful\_highs`/`meaningful\_lows` across multiple evaluations

&#x20; - `SWING\_EXCLUDED:<ts>:non\_extending\_incompatible` present in event log

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R26 — Unresolved distinct from excluded



\- \*\*Test name:\*\* `test\_r26\_unresolved\_distinct\_from\_excluded`

\- \*\*Requirement:\*\* R26

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* Two swings: one with insufficient evidence (unresolved), one with incompatible evidence (excluded).

\- \*\*Assertions:\*\*

&#x20; - Unresolved swing emits `SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict`

&#x20; - Excluded swing emits `SWING\_EXCLUDED:<ts>:non\_extending\_incompatible`

&#x20; - Neither appears in `meaningful\_highs`/`meaningful\_lows`

&#x20; - Only excluded appears in `excluded\_swings`

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R29 — Bootstrap reference not auto-meaningful



\- \*\*Test name:\*\* `test\_r29\_bootstrap\_reference\_not\_auto\_meaningful`

\- \*\*Requirement:\*\* R29

\- \*\*Spec:\*\* §5 Phase 1

\- \*\*Fixture:\*\* Phase 1 HIGH and LOW, then a second HIGH that has no valid opposite-kind evidence.

\- \*\*Assertions:\*\*

&#x20; - Phase 1 swings are admitted with `CLASSIFICATION\_UNRESOLVED`

&#x20; - Second HIGH is classified (using Phase 1 HIGH as reference) but is NOT auto-meaningful just because it has a reference

&#x20; - Second HIGH's admission depends on opposite-kind consistency

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R30 — Phase 2 gating



\- \*\*Test name:\*\* `test\_r30\_phase2\_gating`

\- \*\*Requirement:\*\* R30

\- \*\*Spec:\*\* §5 Phase 2, invariant 28

\- \*\*Fixture:\*\* A sequence that reaches 2 HH + 2 HL. Then additional swings.

\- \*\*Assertions:\*\*

&#x20; - Before 2 HH + 2 HL: no `PHASE2` event (if such an event exists; or check that admitted swings accumulate)

&#x20; - After 2 HH + 2 HL: Phase 2 established (existing behavior for UPTREND)

\- \*\*Baseline:\*\* FAILS (or PARTIAL — current code establishes trends without explicit Phase 1/2 state).

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R31 — No invented bootstrap



\- \*\*Test name:\*\* `test\_r31\_phase1\_no\_invented\_bootstrap`

\- \*\*Requirement:\*\* R31

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* Phase 1 swings (must use Amendment 05's bootstrap rules, not invented rules).

\- \*\*Assertions:\*\*

&#x20; - Phase 1 admission follows Amendment 05's rule (first HIGH and first LOW of episode)

&#x20; - No additional bootstrap rule (e.g., "first 3 swings" or "first 100 candles") is applied

\- \*\*Baseline:\*\* FAILS (or PARTIAL — current code uses `SWING\_MEANINGFUL\_PHASE1` naming but admits everything).

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R32 — Active sequence excludes unresolved



\- \*\*Test name:\*\* `test\_r32\_active\_sequence\_excludes\_unresolved`

\- \*\*Requirement:\*\* R32

\- \*\*Spec:\*\* §5

\- \*\*Fixture:\*\* Phase 1 HIGH, Phase 1 LOW, and a non-bootstrap swing that is unresolved (conflicting evidence).

\- \*\*Assertions:\*\*

&#x20; - Phase 1 swings ARE in `meaningful\_highs`/`meaningful\_lows` (exception per Amendment 05: they are admitted despite `CLASSIFICATION\_UNRESOLVED`)

&#x20; - Non-bootstrap unresolved swing is NOT in `meaningful\_highs`/`meaningful\_lows`

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R34 — Classification precedes admission



\- \*\*Test name:\*\* `test\_r34\_classification\_precedes\_admission`

\- \*\*Requirement:\*\* R34

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* Any multi-swing sequence.

\- \*\*Assertions:\*\* For every admitted swing (except Phase 1), a classification record exists before it appears in `meaningful\_highs`/`meaningful\_lows`.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R38 — Excluded does not replace reference



\- \*\*Test name:\*\* `test\_r38\_excluded\_does\_not\_replace\_reference`

\- \*\*Requirement:\*\* R38

\- \*\*Spec:\*\* §6, invariant 26

\- \*\*Fixture:\*\* Phase 1 HIGH admitted as reference, then a second HIGH excluded. Then a third HIGH.

\- \*\*Assertions:\*\*

&#x20; - Third HIGH's reference is the Phase 1 HIGH, not the excluded one

&#x20; - Classification of third HIGH is computed against Phase 1 HIGH

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R42 — Initial classification established later



\- \*\*Test name:\*\* `test\_r42\_initial\_classification\_established\_later`

\- \*\*Requirement:\*\* R42

\- \*\*Spec:\*\* §6, invariant 29

\- \*\*Fixture:\*\* A swing that is `CLASSIFICATION\_UNRESOLVED` at evaluation N (no reference). Then at evaluation N+1, a reference exists (per row 4 scenario). 

\- \*\*Note:\*\* Row 4 is rare — first-of-kind is Phase 1 (which is permanent). Non-bootstrap unresolved-without-classification requires all prior same-kind to be unresolved/excluded. Fixture construction is nontrivial.

\- \*\*Assertions:\*\* At N: classification None. At N+1: classification established.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.

\- \*\*Alternative:\*\* if constructing this fixture is impractical, note as "not constructively testable in current engine; covered by design reasoning + code review."



\### T-R44 — Classification and participation separate



\- \*\*Test name:\*\* `test\_r44\_classification\_participation\_separate`

\- \*\*Requirement:\*\* R44

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* A swing that is classified (HH) but unresolved (insufficient opposite-kind evidence).

\- \*\*Assertions:\*\*

&#x20; - Classification is available ("HH")

&#x20; - Swing is not admitted

&#x20; - These two facts are independently observable

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R45 — Unresolved not controlling



\- \*\*Test name:\*\* `test\_r45\_unresolved\_not\_controlling`

\- \*\*Requirement:\*\* R45

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* Established UPTREND with controlling HL. A subsequent HL swing is unresolved (conflicting evidence).

\- \*\*Assertions:\*\*

&#x20; - Unresolved HL is not the controlling level

&#x20; - `controlling\_level` remains the previously admitted controlling HL

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R46 — Unresolved event exposure



\- \*\*Test name:\*\* `test\_r46\_swing\_confirmed\_unresolved\_event`

\- \*\*Requirement:\*\* R46

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* Same as T-R26.

\- \*\*Assertions:\*\*

&#x20; - `SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict` present for unresolved

&#x20; - `SWING\_CONFIRMED\_UNRESOLVED:<ts>:bootstrap` present for Phase 1

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R47 — Unresolved excluded from meaningful



\- \*\*Test name:\*\* `test\_r47\_unresolved\_excluded\_from\_meaningful`

\- \*\*Requirement:\*\* R47

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* Same as T-R26.

\- \*\*Assertions:\*\* Unresolved swings are not in `meaningful\_highs`/`meaningful\_lows`.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R48 — Reconsideration bounded



\- \*\*Test name:\*\* `test\_r48\_reconsideration\_bounded`

\- \*\*Requirement:\*\* R48

\- \*\*Spec:\*\* §6, invariant 30

\- \*\*Fixture:\*\* An unresolved swing, then multiple new confirmed swings in one evaluation.

\- \*\*Assertions:\*\* No recursive or duplicate events; the unresolved swing's status is recomputed once per evaluation (observable: no oscillation).

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R49 — Classification established on reconsideration



\- \*\*Test name:\*\* `test\_r49\_classification\_established\_on\_reconsideration`

\- \*\*Requirement:\*\* R49

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* A swing that was `CLASSIFICATION\_UNRESOLVED` at N; reference becomes available at N+1.

\- \*\*Assertions:\*\* Classification established at N+1. Once established, cannot be recalculated at N+2.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R50 — Admission gate



\- \*\*Test name:\*\* `test\_r50\_admission\_requires\_consistent\_evidence`

\- \*\*Requirement:\*\* R50

\- \*\*Spec:\*\* §6

\- \*\*Fixture:\*\* Two swings with identical same-kind classification, one with consistent opposite-kind evidence, one with inconsistent.

\- \*\*Assertions:\*\* Consistent one admitted, inconsistent one excluded/unresolved.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R51 — Excluded persists



\- \*\*Test name:\*\* `test\_r51\_excluded\_persists\_no\_reinstate`

\- \*\*Requirement:\*\* R51

\- \*\*Spec:\*\* §6, invariant 31

\- \*\*Fixture:\*\* Same as T-R24.

\- \*\*Assertions:\*\* After exclusion, subsequent evaluations do not re-admit the swing.

\- \*\*Baseline:\*\* FAILS.

\- \*\*Post-Round-2:\*\* PASSES.



\### T-R57 — Invalidated non-controlling, episode-scoped



\- \*\*Test name:\*\* `test\_r57\_invalidated\_non\_controlling\_episode\_scoped`

\- \*\*Requirement:\*\* R57 (full)

\- \*\*Spec:\*\* §8, Amendment 06 §C

\- \*\*Fixture:\*\* UPTREND established, invalidated, then replacement episode with its own Phase 1 swings.

\- \*\*Assertions:\*\*

&#x20; - `controlling\_level = None` in TRANSITION

&#x20; - Replacement episode's first HIGH/LOW emit `SWING\_CONFIRMED\_UNRESOLVED:bootstrap` (prior swings not used as references)

&#x20; - Prior-episode swings do not appear in replacement episode's `meaningful\_highs`/`meaningful\_lows`

\- \*\*Baseline:\*\* PARTIAL — `controlling\_level = None` already implemented (from Phase A), but episode-scoped reference rules are not.

\- \*\*Post-Round-2:\*\* PASSES (fully).



\## Regression tests (must pass after each round)



These tests are existing and must not regress:



\- `test\_r56\_replacement\_downtrend\_established\_after\_uptrend\_invalidation\_is\_not\_transition` (R56)

\- `test\_r59\_no\_range\_breakout\_recorded\_while\_trend\_is\_established` (R59)

\- `test\_r65\_range\_penetration\_is\_decided\_by\_next\_completed\_candle` (R65)

\- `test\_r68\_established\_uptrend\_persists\_after\_close\_above\_last\_swing\_high` (R68)

\- All T1–T6 trend tests

\- `test\_r13\_opposing\_swing\_replacement\_records\_old\_and\_new\_reference` (R13)

\- All 326 baseline tests



\## Test count summary



| Round | New tests | Full suite after |

|---|---|---|

| Baseline (pre-Round-1) | 0 | 326 |

| Round 1 | 3 | 329 |

| Round 2 | 23 | 352 |



If test counts differ at any point, investigate before proceeding.

