\# MS-0.1A Phase B — Design: Admission State Model



\*\*Status:\*\* Engineering design document. Not a specification amendment.

\*\*Audience:\*\* Phase B implementation (the VIOLATED/MISSING requirements from the fresh conformance audit).

\*\*Spec authority:\*\* `docs/strategy/ms-0.1a-market-structure-spec.md` as amended by 03, 04, 05, 06.

\*\*Approved:\*\* 2026-10-25.



\## 1. Scope



This document defines the implementation approach for Phase B: the rework of the market-structure engine's meaningfulness, admission, classification-recording, and unresolved/excluded state. It does not change candidate detection, confirmation, opposing-swing handling, range boundary logic, or regime classification beyond the input they receive.



\*\*Out of scope:\*\*

\- Candidate identification (§3) — unchanged.

\- Confirmation (§4) — unchanged.

\- Opposing-swing lifecycle including R13 rebinding — unchanged.

\- RANGE boundary logic and breakout confirmation (§9) — unchanged.

\- Regime classification structure (§7–§10) — unchanged in form; only the meaningful set fed into it changes.



\*\*In scope (Phase B requirements):\*\*



Group B (state model): R23, R24, R26, R30, R38, R40, R41, R42, R44, R46, R47, R48, R49, R51.



Group A (admission procedure): R15, R18, R19, R22, R29, R31, R32, R34, R45, R50, R57.



\*\*Regression verification:\*\* R56, R59, R65, R68.



\## 2. What exists today



The current `\_meaningful\_swings()` admits every confirmed swing unconditionally. It emits `SWING\_MEANINGFUL\_PHASE1` for the first HIGH and first LOW, and `SWING\_MEANINGFUL` for every subsequent confirmed swing. It performs no same-kind classification check, no opposite-kind consistency check, and no unresolved/excluded state tracking.



This is the central defect underlying all Group A and Group B requirements.



\## 3. Conceptual model



The spec distinguishes three layers of information about a confirmed swing:



| Layer | What it records | Spec basis |

|---|---|---|

| Confirmation evidence | The swing was confirmed by a completed close beyond the opposing extreme | §4 |

| Classification | The swing's same-kind relationship (HH/LH/HL/LL/EQ) or CLASSIFICATION\_UNRESOLVED | §6, amendment 05, amendment 06 |

| Admission | Whether the swing is in the active structural sequence, unresolved, or excluded | §5, §6, amendment 06 |



These are conceptually separate. A confirmed swing can be:



\- Classified AND admitted (typical Phase 2 swing).

\- CLASSIFICATION\_UNRESOLVED AND admitted (Phase 1 bootstrap observation, per amendment 05).

\- Classified AND unresolved (same-kind relationship known but opposite-kind evidence insufficient, per §6 + amendment 06 Section B).

\- Classified AND excluded (same-kind and opposite-kind evidence both complete and demonstrably incompatible, per amendment 06 Section B).

\- CLASSIFICATION\_UNRESOLVED AND unresolved (both classification and admission deferred).

\- CLASSIFICATION\_UNRESOLVED AND excluded — not a valid combination per amendment 06 (exclusion requires determinable classification).



\## 4. State representation



\### 4.1 \_Confirmed stays unchanged



`\_Confirmed` remains a frozen record of confirmation evidence: `candidate` + `confirmed\_at`. Adding admission or classification state to `\_Confirmed` would conflate evidence with decisions and break immutability of confirmation records. The choice is architectural (evidence vs. decision), not just test convenience.



\### 4.2 New types



&#x20;   @dataclass(frozen=True, slots=True)

&#x20;   class \_ClassificationRecord:

&#x20;       swing\_timestamp: datetime

&#x20;       classification: str | None  # "HH" / "LH" / "HL" / "LL" / "EQ\_HIGH" / "EQ\_LOW" / None

&#x20;       reference\_timestamp: datetime | None  # same-kind admitted swing used as reference

&#x20;       is\_bootstrap: bool  # True for Phase 1 CLASSIFICATION\_UNRESOLVED swings



&#x20;   @dataclass(frozen=True, slots=True)

&#x20;   class \_AdmissionLedger:

&#x20;       admitted: tuple\[\_Confirmed, ...]

&#x20;       unresolved: tuple\[\_Confirmed, ...]

&#x20;       excluded: tuple\[\_Confirmed, ...]

&#x20;       classification: dict\[datetime, \_ClassificationRecord]

&#x20;       episode\_start: datetime | None



&#x20;   @dataclass(frozen=True, slots=True)

&#x20;   class \_AdmissionResult:

&#x20;       ledger: \_AdmissionLedger

&#x20;       events: tuple\[str, ...]



\### 4.3 Changes to MarketStructureState



Add one field:



&#x20;   excluded\_swings: tuple\[SwingPoint, ...]  # confirmed swings excluded from the active sequence



All existing fields preserved. This addition is backwards-compatible per §11 ("at minimum").



\## 5. \_meaningful\_swings signature and behavior



\### 5.1 Signature



&#x20;   def \_meaningful\_swings(

&#x20;       self,

&#x20;       confirmed: Sequence\[\_Confirmed],

&#x20;       eligible: Sequence\[MarketCandle],

&#x20;       events: list\[str],

&#x20;   ) -> \_AdmissionResult:



`eligible` is the candle list (needed to determine episode boundaries from prior invalidations). The method returns an `\_AdmissionResult` containing the ledger and the events it produced. The caller (`evaluate`) extends its `events` list with `result.events`.



\### 5.2 Algorithm



Process `confirmed` in chronological order. For each swing:



1\. Determine episode start. Compute the episode start as the last invalidation timestamp or None for the first episode. Swings before the episode start belong to a prior episode and are historical.



2\. Check if the swing is a Phase 1 bootstrap. A swing is Phase 1 bootstrap if no prior admitted same-kind swing exists in the current episode and it is the first confirmed HIGH or first confirmed LOW of the episode. Per amendment 05 §A: such a swing is admitted with CLASSIFICATION\_UNRESOLVED (permanent within episode).



3\. Determine same-kind classification. Per §6 + amendment 06 Section A:

&#x20;  - Find the most recent admitted same-kind swing in the current episode.

&#x20;  - If found: classify as HH/LH/HL/LL/EQ\_\* by comparing prices/zones.

&#x20;  - If not found: CLASSIFICATION\_UNRESOLVED.



4\. Determine admission.

&#x20;  - Phase 1 bootstrap: admitted.

&#x20;  - Else if same-kind classification is CLASSIFICATION\_UNRESOLVED: unresolved.

&#x20;  - Else: check opposite-kind structural consistency:

&#x20;    - Complete and demonstrably incompatible evidence: excluded.

&#x20;    - Insufficient or conflicting-but-not-incompatible evidence: unresolved.

&#x20;    - Complete and consistent evidence: admitted.



5\. Record the classification record: classification, reference\_timestamp, is\_bootstrap.



6\. Emit the event per the event contract (§6).



\### 5.3 Reconsideration (observation, not mechanism)



This document does not implement an explicit "reconsideration pass." Re-derivation is the reconsideration: each `evaluate()` call re-processes all confirmed swings with the current candles. An unresolved swing from evaluation N becomes admitted at N+1 if the additional candles provide the missing evidence.



Invariant 30's "one pass per admission/exclusion" is satisfied trivially: one pass = one `evaluate()` call. No recursive re-triggering exists because there is no inner loop.



\## 6. Event contract



Final decisions per the design questions:



| Situation | Event |

|---|---|

| Confirmation (existing) | SWING\_CONFIRMED:<ts> |

| Phase 1 bootstrap admission | SWING\_MEANINGFUL\_PHASE1:<ts> |

| Phase 2 classification successful + admitted | SWING\_MEANINGFUL:<ts> |

| Phase 2 classification successful, still unresolved | SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict |

| Phase 1 bootstrap, forever unresolved | SWING\_CONFIRMED\_UNRESOLVED:<ts>:bootstrap |

| Swing excluded as non-extending | SWING\_EXCLUDED:<ts>:non\_extending\_incompatible |

| Successful classification (intermediate) | (silent — no separate event) |



Event ordering: within a single `evaluate()` call, events are emitted in chronological order of the swing's timestamp\_open, with the specific event per swing as decided above.



\## 7. Transition table



The full transition table is in `docs/design/ms-0.1a-phase-b-transition-table.md`.



\## 8. Implementation sequence



\### 8.1 Round 1 — Foundation (Group B partial)



Files changed:

\- src/trading\_system/strategy/market\_structure/engine.py (types + \_meaningful\_swings partial rewrite + \_state signature)

\- src/trading\_system/domain/models.py (MarketStructureState.excluded\_swings field)

\- tests/unit/test\_market\_structure\_engine.py (new tests for R40, R41, R22 partial)



Behavior: Phase 1 swings get CLASSIFICATION\_UNRESOLVED. Non-bootstrap swings get classified against most recent admitted same-kind reference. Every classified swing is still admitted (no gate). No exclusions yet.



Tests target: R40, R41, plus partial-coverage tests for R22, R32. Baseline regressions from R56, R59, R65, R68 must still pass.



Expected full-suite count after Round 1: 326 + 3 = 329 passed.



\### 8.2 Round 2 — Admission gate (Group A + Group B remaining)



Files changed:

\- src/trading\_system/strategy/market\_structure/engine.py (admission gate + unresolved/excluded population + event emission)

\- tests/unit/test\_market\_structure\_engine.py (all remaining Phase B tests)



Behavior: Admission gate enforced. Swings classified but not admitted become unresolved or excluded. Unresolved/excluded excluded from meaningful\_highs/meaningful\_lows. Events emitted per §6.



Tests target: R15, R18, R19, R22, R23, R24, R26, R29, R30, R31, R32, R34, R38, R42, R44, R45, R46, R47, R48, R49, R50, R51, R57. Full regression on R56, R59, R65, R68.



Expected full-suite count after Round 2: 329 + 23 = 352 passed.



\### 8.3 Regression verification (both rounds)



After each round:

\- R56: test\_r56\_replacement\_downtrend\_established\_after\_uptrend\_invalidation\_is\_not\_transition must pass.

\- R59: test\_r59\_no\_range\_breakout\_recorded\_while\_trend\_is\_established must pass.

\- R65: test\_r65\_range\_penetration\_is\_decided\_by\_next\_completed\_candle must pass.

\- R68: test\_r68\_established\_uptrend\_persists\_after\_close\_above\_last\_swing\_high must pass.



If any fails, the change has regressed prior work. Investigate before proceeding.



\## 9. Phase B test list



The full test list is in `docs/design/ms-0.1a-phase-b-test-list.md`.



\## 10. Regression plan



After Round 2, the following must still pass unchanged:

\- All Phase A tests: R56, R59, R65, R68.

\- All trend tests: T1–T6.

\- All R13 tests.

\- All prior baseline tests.



Any regression is a Phase B defect that must be addressed before the round completes.



\## 11. Open items deferred to implementation



\- Exact data structure for \_ClassificationRecord.classification — str | None or a small enum.

\- Whether reference\_timestamp should be a datetime or an index into confirmed.

\- Whether to validate excluded\_swings in MarketStructureState.\_\_post\_init\_\_.

\- Whether \_meaningful\_swings needs eligible at all or whether episode start can be derived from confirmed alone.



\## 12. Revision history



\- 2026-10-25: Initial draft, based on fresh conformance audit and Amendments 05/06.

\- 2026-10-25: Finalized. Five design decisions accepted, two-round split approved.

