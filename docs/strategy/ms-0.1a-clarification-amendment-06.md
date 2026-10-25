\# MS-0.1A Clarification Amendment 06 — Reference Eligibility, Exclusion Criteria, and Episode Isolation



\*\*Status:\*\* Documentation-only clarification. No implementation or test files are changed in this amendment.

\*\*Canonical target:\*\* `docs/strategy/ms-0.1a-market-structure-spec.md`

\*\*Resolves:\*\* Three specification gaps identified during Phase B design:

\- G4: whether a classified-but-unresolved swing can serve as a same-kind reference

\- G5: what distinguishes "explicitly excluded as non-extending" from "unresolved"

\- G6: whether prior-episode swings can serve as classification references for a replacement episode



\## Section A — Reference eligibility (§6)



Only an admitted meaningful swing may serve as a same-kind classification reference. A confirmed swing that is unresolved (whether due to missing same-kind reference or to insufficient/conflicting opposite-kind evidence) does not replace the same-kind reference, and does not become a reference for subsequent same-kind swings while it remains unresolved.



An excluded swing does not serve as a same-kind reference under any circumstance. This is already required by invariant 26 and is restated here to make the reference-eligibility rule complete.



The same-kind reference for a confirmed swing is therefore always the most recent \*admitted\* meaningful swing of the same kind in the current episode, even if there exist more recent same-kind swings that are unresolved or excluded.



\## Section B — Exclusion criteria (§6)



A confirmed swing is \*\*excluded as non-extending\*\* only when all of the following hold:



1\. Its same-kind classification is determinable (i.e., a valid same-kind reference exists, so the swing is not `CLASSIFICATION\_UNRESOLVED`).

2\. Its opposite-kind evidence is complete (a swing of the opposite kind exists at the relevant reference position, or the absence of such a swing is itself determinable).

3\. The combination of same-kind classification and opposite-kind evidence is demonstrably incompatible with extension of any directional structure.



The canonical incompatible pattern is:



\- A HIGH classified as `HH` whose supporting opposite-kind swing is classified `LL`.

\- A LOW classified as `LL` whose supporting opposite-kind swing is `HH`.

\- Symmetric mirror cases.



Such a swing cannot participate in any UPTREND (requires HH + HL or HL + HH) or DOWNTREND (requires LH + LL or LL + LH) establishment. Its exclusion is therefore a property of the evidence, not of any subsequent evaluation.



If the same-kind classification is available but the opposite-kind evidence is \*\*insufficient\*\* or \*\*conflicting in a way that is not demonstrably incompatible\*\*, the swing remains \*\*unresolved\*\*, not excluded. Unresolved swings are reconsiderable at later evaluations per §6. Excluded swings are not.



This distinction is mechanical: exclusion requires complete evidence that is incompatible; unresolved covers insufficient or conflicting-but-not-incompatible evidence.



\## Section C — Episode isolation (§5, §8)



Prior-episode swings — swings confirmed before the invalidating close of a prior episode — remain historical and auditable but do not serve as classification references for Phase 1 observations of the replacement episode. They also do not count toward directional establishment of the replacement episode (this restates invariant 33).



Consequently, the first confirmed HIGH and first confirmed LOW of a replacement episode are Phase 1 observations with `CLASSIFICATION\_UNRESOLVED` classification per Amendment 05, regardless of the price history of prior-episode swings.



\## Section D — Interaction with existing invariants



This amendment is consistent with:



\- Invariant 26 ("A confirmed swing excluded as non-extending does not replace its same-kind reference and is not silently reinstated"): Section A extends this from "does not replace" to "does not serve as reference."

\- Invariant 29 (classification and reference are immutable once established): Section A clarifies which swings establish those immutably recorded references.

\- Invariant 31 ("a swing explicitly excluded as non-extending is not re-evaluated or reinstated"): Section B defines what "explicitly excluded as non-extending" means mechanically.

\- Invariant 33 (transition episode membership): Section C extends invariant 33's scope from counting to reference eligibility.



\## Section E — Consequences for the transition table



The Phase B design's transition table (Row 6, Row 7, Row 9, Row 10) is fully determined by the combination of:



\- Amendment 05: Phase 1 bootstrap and reconsideration scope.

\- This amendment (06): reference eligibility (Section A), exclusion criteria (Section B), episode isolation (Section C).



Specifically:



\- A swing classified `HH` with opposite evidence missing is \*\*unresolved\*\* (Row 6). It does not become a reference.

\- A swing classified `HH` with opposite evidence `LL` is \*\*excluded\*\* (Row 7). It does not become a reference.

\- A swing admitted (Row 5) becomes the same-kind reference for subsequent swings; this reference is immutable per invariant 29.

\- A replacement episode's Phase 1 swings are `CLASSIFICATION\_UNRESOLVED` because prior-episode swings are not eligible references (Row 10).



\## Scope and change control



This amendment changes documentation only. It does not authorize implementation or test changes in this commit. Phase B implementation must follow the test-first process against the canonical specification as amended.



The current engine (`src/trading\_system/strategy/market\_structure/engine.py`) remains unchanged until Phase B rework begins.

