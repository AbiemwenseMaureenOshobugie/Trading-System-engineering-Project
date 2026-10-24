\# MS-0.1A Clarification Amendment 05 — Phase 1 Bootstrap and Unresolved First-of-Episode Swings



\*\*Status:\*\* Documentation-only clarification. No implementation or test files are changed in this amendment.

\*\*Canonical target:\*\* `docs/strategy/ms-0.1a-market-structure-spec.md`

\*\*Resolves:\*\* Section 5 bootstrap ambiguity (first-of-episode swing classification and reference use).



\## Section A — Phase 1 bootstrap (§5)



When the active structural sequence is empty at the start of evaluation, or becomes empty immediately after invalidation, the following bootstrap rules apply:



1\. The first confirmed HIGH and the first confirmed LOW of the episode are admitted into the active structural sequence as Phase 1 reference observations. Their admission does not depend on same-kind comparison, because no same-kind reference exists within the episode.



2\. Each admitted Phase 1 observation receives `CLASSIFICATION\_UNRESOLVED` as its relationship classification. This classification is permanent within the episode and does not change on later evaluation.



3\. An admitted Phase 1 observation shall serve as the same-kind reference for subsequent confirmed swings of the same kind within the episode. The second swing of that kind is classified against the Phase 1 observation and receives HH or LH (for HIGH) or HL or LL (for LOW), even though the Phase 1 observation itself remains `CLASSIFICATION\_UNRESOLVED`.



4\. Subsequent confirmed swings of each kind are classified against the most recent accepted meaningful same-kind swing in the active sequence, per §6.



\## Section B — Reconsideration scope (§6)



Section 6's reconsideration rule — that an unresolved swing may be reconsidered when a newly confirmed swing receives an admission or exclusion outcome — applies only to swings whose unresolved state arises from conflicting or insufficient same-kind/opposite-kind evidence. It does not apply to the Phase 1 `CLASSIFICATION\_UNRESOLVED` state described in Section A, clause 2.



\## Section C — Phase 2 timing (§5, §7)



Phase 2 begins only when Section 7's directional establishment requirements are satisfied. Phase 1 bootstrap and Phase 2 establishment are governed by the same classification and meaningfulness rules. The only distinction is chronology: Phase 1 consists of the first two admissions (first HIGH, first LOW); Phase 2 begins once the directional establishment threshold is met (2 HH + 2 HL for UPTREND, or 2 LH + 2 LL for DOWNTREND).



\## Section D — Invariant 29 clarification



Invariant 29's clause "an initially unresolved classification may be established later when a valid same-kind reference becomes available" applies only to swings that are unresolved due to conflicting or insufficient evidence (Section B scope). It does not apply to the Phase 1 `CLASSIFICATION\_UNRESOLVED` state, which is permanent within the episode.



\## Section E — Consequences for implementation



This amendment makes the following behaviors explicit contract requirements:



\- The first confirmed HIGH and first confirmed LOW of an episode are admitted as meaningful with `CLASSIFICATION\_UNRESOLVED`.

\- A `CLASSIFICATION\_UNRESOLVED` event (or equivalent) is emitted for each admitted Phase 1 observation.

\- The Phase 1 observation serves as the same-kind reference for subsequent same-kind swings, even though the Phase 1 observation has no HH/LH/HL/LL label.

\- The Phase 1 observation's `CLASSIFICATION\_UNRESOLVED` state is permanent within the episode (no later reference establishes it).

\- Section 6's reconsideration rule continues to apply to deferred (conflict-based) unresolved swings, not to Phase 1 observations.



The current implementation's `\_meaningful\_swings` admits the first HIGH and LOW as `SWING\_MEANINGFUL\_PHASE1` but does not emit a `CLASSIFICATION\_UNRESOLVED` event and does not enforce that subsequent swings follow §5's admission procedure. This is deferred to the Phase B rework, which is unblocked by this amendment.



\## Scope and change control



This amendment resolves documentation only. It does not authorize implementation or test changes in this commit. The Phase B rework must still follow the test-first process against the frozen canonical specification.

