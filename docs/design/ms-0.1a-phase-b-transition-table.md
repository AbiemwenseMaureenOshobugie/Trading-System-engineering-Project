\# MS-0.1A Phase B — Transition Table



\*\*Status:\*\* Companion to `ms-0.1a-phase-b-admission-model.md`. Reference for Phase B implementation and testing.

\*\*Spec authority:\*\* `docs/strategy/ms-0.1a-market-structure-spec.md` as amended by 03, 04, 05, 06.



Each row describes a state consideration for a confirmed swing. The "Governing spec" column cites the exact text that determines the row's outcome.



\## Row 1 — Candidate confirmed



| Field | Value |

|---|---|

| Trigger | A completed H1 candle closes beyond the active opposing swing's extreme. `\_confirm\_candidates` produces a `\_Confirmed`. |

| Governing spec | §4: "A candidate becomes a confirmed swing only after a completed H1 candle closes beyond the extreme of its active opposing swing." |

| Classification | Not determined. Classification is §6, not §4. |

| Admission | Not determined. Admission is §5/§6, not §4. |

| Reference | N/A (pre-classification). |

| Event | `SWING\_CONFIRMED:<ts>` (existing, unchanged). |

| Mutable later | Confirmation itself is immutable; a confirmed swing remains confirmed. Classification and admission are computed from this point. |

| Test | `test\_dual\_candidate\_is\_rejected` (indirect); existing suite covers confirmation. |



\## Row 2 — First HIGH or LOW of an episode



| Field | Value |

|---|---|

| Trigger | Confirmed swing with no prior admitted same-kind swing in the current episode, and it is the first of its kind. |

| Governing spec | §5 Phase 1; Amendment 05 §A clauses 1–2: "the first confirmed HIGH and the first confirmed LOW of the episode are admitted into the active structural sequence as Phase 1 reference observations with CLASSIFICATION\_UNRESOLVED classification... This classification is permanent within the episode." |

| Classification | `CLASSIFICATION\_UNRESOLVED` (permanent within episode). |

| Admission | Admitted (as Phase 1 reference observation). |

| Reference | Serves as same-kind reference for subsequent swings of the same kind within the episode (Amendment 05 §A clause 3). |

| Event | `SWING\_MEANINGFUL\_PHASE1:<ts>` (Phase 1 admission) AND `SWING\_CONFIRMED\_UNRESOLVED:<ts>:bootstrap` (Amendment 05's permanent unresolved classification). |

| Mutable later | No — classification is permanent within the episode (Amendment 05 §A clause 2). Admission is permanent unless the episode is invalidated. |

| Test | `test\_r41\_phase1\_swing\_classification\_unresolved` (Round 1). |



\## Row 3 — Classification available



| Field | Value |

|---|---|

| Trigger | A confirmed swing (not Phase 1) with a valid admitted same-kind reference in the current episode. |

| Governing spec | §6: "For a candidate confirmed HIGH, the reference is the most recent previously accepted meaningful HIGH in the active structural sequence... Confirmed HIGH above its same-kind reference → HH." |

| Classification | HH, LH, HL, LL, EQ\_HIGH, or EQ\_LOW, determined by price comparison to the reference. |

| Admission | Determined by row 5, 6, or 7 based on opposite-kind evidence. |

| Reference | The reference is recorded and frozen (invariant 29). |

| Event | Silent (intermediate — Decision 2). |

| Mutable later | No — classification and reference are immutable (invariant 29). |

| Test | `test\_r40\_classification\_and\_reference\_recorded` (Round 1). |



\## Row 4 — No same-kind reference available (non-bootstrap)



| Field | Value |

|---|---|

| Trigger | A confirmed swing (not Phase 1) with no valid admitted same-kind reference in the current episode. |

| Governing spec | §6: "If no accepted meaningful same-kind reference exists, the engine records CLASSIFICATION\_UNRESOLVED; it must not invent a bootstrap reference." |

| Classification | `CLASSIFICATION\_UNRESOLVED`. |

| Admission | Unresolved (deferred). |

| Reference | None. |

| Event | `SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict` (Decision 3). |

| Mutable later | Yes — reconsiderable per §6 when a reference becomes available. |

| Test | `test\_r42\_initial\_classification\_established\_later` (Round 2). |



Note: this case is rare in practice — it requires a same-kind swing that is not the first of its kind (Phase 1 already handled that) yet has no admitted same-kind reference (e.g., all prior same-kind swings are unresolved or excluded). Row 4 exists to be complete.



\## Row 5 — Consistent evidence, admitted



| Field | Value |

|---|---|

| Trigger | Classified swing (row 3) whose same-kind classification and opposite-kind evidence are consistent with active-chain extension. |

| Governing spec | §6: "A swing is admitted to the active structural chain only when its same-kind classification and the available opposite-kind structural evidence are consistent with the active structural sequence." |

| Classification | Row 3 classification. |

| Admission | Admitted. |

| Reference | Becomes new same-kind reference for subsequent swings. |

| Event | `SWING\_MEANINGFUL:<ts>` (existing). |

| Mutable later | No (admission is permanent within the episode). |

| Test | `test\_r19\_admission\_requires\_active\_chain\_acceptance` (Round 2). |



\## Row 6 — Insufficient/conflicting evidence, unresolved



| Field | Value |

|---|---|

| Trigger | Classified swing whose opposite-kind evidence is insufficient or conflicting but not demonstrably incompatible. |

| Governing spec | §6: "When same-kind classification and available opposite-kind structural evidence conflict, or evidence is insufficient to determine active-chain participation, the swing remains a confirmed observation but is unresolved for that evaluation." Amendment 06 §B: "If the same-kind classification is available but the opposite-kind evidence is insufficient or conflicting in a way that is not demonstrably incompatible, the swing remains unresolved, not excluded." |

| Classification | Row 3 classification (available, not `CLASSIFICATION\_UNRESOLVED`). |

| Admission | Unresolved. |

| Reference | Not a reference (Amendment 06 §A: "A confirmed swing that is unresolved does not replace the same-kind reference and does not serve as a reference"). |

| Event | `SWING\_CONFIRMED\_UNRESOLVED:<ts>:conflict`. |

| Mutable later | Yes — reconsiderable per §6. |

| Test | `test\_r45\_unresolved\_not\_controlling` (Round 2). |



\## Row 7 — Complete and incompatible evidence, excluded



| Field | Value |

|---|---|

| Trigger | Classified swing whose same-kind classification and opposite-kind evidence are both complete AND demonstrably incompatible with any directional extension. |

| Governing spec | §6: "A swing explicitly excluded as non-extending remains excluded and is not re-evaluated or reinstated." Amendment 06 §B: "A confirmed swing is excluded as non-extending only when its same-kind classification is determinable, its opposite-kind evidence is complete, and the combination is demonstrably incompatible... The canonical incompatible pattern is a HIGH classified HH whose supporting opposite-kind swing is LL (or symmetric mirror cases)." |

| Classification | Row 3 classification. |

| Admission | Excluded. |

| Reference | Not a reference (invariant 26; Amendment 06 §A). |

| Event | `SWING\_EXCLUDED:<ts>:non\_extending\_incompatible` (Decision 4). |

| Mutable later | No (invariant 31: "a swing explicitly excluded as non-extending is not re-evaluated or reinstated"). |

| Test | `test\_r24\_excluded\_swing\_not\_reinstated` (Round 2). |



\## Row 8 — Previously unresolved swing, reconsideration



| Field | Value |

|---|---|

| Trigger | A later `evaluate()` call includes new candles or additional confirmed swings, and a previously unresolved swing's evidence now resolves. |

| Governing spec | §6: "an initially unresolved classification may be established later when a valid same-kind reference becomes available... Admission is reconsidered separately using the updated confirmed structural evidence." Invariant 30: "A newly confirmed swing's admission or exclusion triggers one reconsideration pass over unresolved swings in chronological order." |

| Classification | Establishes classification if previously `CLASSIFICATION\_UNRESOLVED` and reference now available. Immutable once established (invariant 29). |

| Admission | Re-derived: admitted (row 5), excluded (row 7), or remains unresolved (row 6). |

| Reference | Recorded if newly classified. |

| Event | Prior `SWING\_CONFIRMED\_UNRESOLVED` appears in prior evaluation; new event (from row 5/6/7 outcome) appears in current evaluation. |

| Mutable later | Classification: no (invariant 29 once established). Admission: yes if still unresolved. |

| Test | `test\_r49\_classification\_established\_on\_reconsideration` (Round 2). |



Note: per the design doc §5.3, reconsideration is implemented as pure re-derivation. The "pass" bound (invariant 30) is one pass per `evaluate()` call — satisfied trivially because there is no inner loop.



\## Row 9 — Current episode invalidated



| Field | Value |

|---|---|

| Trigger | A completed H1 close beyond the controlling swing's boundary (§8). |

| Governing spec | §8: "UPTREND → completed H1 close below controlling HL. DOWNTREND → completed H1 close above controlling LH." §8: "Invalidated structure remains historical but becomes inactive and non-controlling." |

| Classification | For prior-episode swings: unchanged (already classified or unresolved). |

| Admission | Prior-episode swings become inactive (not in current active sequence). |

| Reference | Prior-episode swings cannot serve as classification references for new-episode Phase 1 observations (Amendment 06 §C). |

| Event | `UPTREND\_INVALIDATED` or `DOWNTREND\_INVALIDATED` (existing). |

| Mutable later | No. |

| Test | `test\_r57\_invalidated\_non\_controlling\_episode\_scoped` (Round 2). |



\## Row 10 — First swing of replacement episode



| Field | Value |

|---|---|

| Trigger | First confirmed HIGH or LOW after an invalidation. |

| Governing spec | §8 (amended): "A transition episode begins at the first completed candle that closes beyond the controlling level of an established regime." Amendment 05 §A: Phase 1 bootstrap applies when "the active structural sequence is empty." Amendment 06 §C: prior-episode swings are not eligible references. |

| Classification | `CLASSIFICATION\_UNRESOLVED` (permanent within the new episode). |

| Admission | Admitted (Phase 1). |

| Reference | Serves as reference for subsequent swings in the new episode. |

| Event | Same as row 2. |

| Mutable later | No (unless new episode itself invalidated). |

| Test | `test\_r57\_invalidated\_non\_controlling\_episode\_scoped` (Round 2, covers this row too). |



\## Row 11 — Identical inputs



| Field | Value |

|---|---|

| Trigger | `evaluate()` called with the same `(candles, cutoff)` as a prior call. |

| Governing spec | Invariant 24: "Identical candles and cutoff produce identical state and structural events." Invariant 31: "Re-evaluation never rewrites prior evaluation output." |

| Classification | Identical to prior. |

| Admission | Identical to prior. |

| Reference | Identical to prior. |

| Event | Identical event log. |

| Mutable later | N/A. |

| Test | `test\_t6\_regime\_persistence\_across\_evaluations` (existing, extends to full state). |



\## Cross-reference: spec requirements → transition table rows



| Requirement | Rows | Notes |

|---|---|---|

| R15, R18, R19 (confirmation ≠ meaningfulness) | Row 2, Row 5 | Admission gate enforces distinction |

| R22 (structural relationships determine participation) | Row 3 → Row 5/6/7 | Classification precedes admission |

| R23 (inactive auditable, not classifying) | Row 9 | Prior-episode swings inactive |

| R24 (excluded not reinstated) | Row 7 | Exclusion permanent |

| R26 (unresolved ≠ excluded) | Row 6 vs. Row 7 | Distinct outcomes |

| R29 (bootstrap not auto-meaningful) | Row 2 | Phase 1 has `CLASSIFICATION\_UNRESOLVED` |

| R30 (Phase 2 gating) | Row 5 | Admitted swings only |

| R31 (no invented bootstrap) | Row 2 | Bootstrap is amendment 05's specific rule |

| R32 (active sequence excludes unresolved) | Row 6 vs. Row 2 | Phase 1 admitted despite unresolved (exception); non-bootstrap unresolved not admitted |

| R34 (classification precedes admission) | Row 3 → Row 5 | Order enforced |

| R38 (excluded not a reference) | Row 7 | Explicitly not a reference |

| R40 (classification + reference recorded) | Row 3 | Recorded in `\_ClassificationRecord` |

| R41 (`CLASSIFICATION\_UNRESOLVED` when no reference) | Row 2, Row 4 | Both cases emit None |

| R42 (later establishment of initial classification) | Row 8 | Reconsideration |

| R44 (classification vs. participation separate) | Row 3 vs. Row 5/6/7 | Two-stage decision |

| R45 (unresolved not controlling) | Row 6 | Not admitted, not controlling |

| R46 (`SWING\_CONFIRMED\_UNRESOLVED` event) | Row 2, Row 4, Row 6 | Emitted with reason suffix |

| R47 (unresolved excluded from meaningful) | Row 6 | Not in `meaningful\_highs/lows` |

| R48 (bounded reconsideration) | Row 8 | One pass per evaluation |

| R49 (classification established from prior unresolved) | Row 8 | Per §6 |

| R50 (admission requires consistent evidence) | Row 5 vs. Row 6 | Gate |

| R51 (excluded persists) | Row 7 | Invariant 31 |

| R57 (invalidated non-controlling, episode-scoped) | Row 9, Row 10 | Invalidation resets episode |

| R56, R59, R65, R68 (regression) | Rows 5, 6, 9 | Prior behaviors preserved |

