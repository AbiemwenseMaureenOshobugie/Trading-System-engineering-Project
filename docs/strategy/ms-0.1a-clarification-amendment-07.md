# MS-0.1A Clarification Amendment 07 — Admission Gate, Supporting Evidence, Bootstrap Support, and Episode Boundaries

**Status:** Documentation-only clarification. No implementation or test files are changed in this amendment.

**Canonical target:** `docs/strategy/ms-0.1a-market-structure-spec.md`

**Implementation status:** Round 2 implementation remains on hold until this amendment is reviewed and frozen.

## Purpose

This amendment makes the admission gate introduced by Amendment 06 deterministic and auditable.

It defines:

- How a candidate swing selects its supporting opposite-kind swing.
- How the candidate is classified against its same-kind reference.
- How bootstrap support permits the first non-bootstrap admissions.
- Which compatibility pairs admit, exclude, or leave a swing unresolved.
- How excluded swings are represented.
- How invalidation closes establish new structural episodes.
- How classification, admission, and audit events remain distinct.

This amendment does not introduce a RANGE admission formula or alter the handbook's established UPTREND and DOWNTREND requirements.

## Section A — Supporting opposite-kind swing

For a confirmed candidate swing with kind K, same-kind reference R, and confirmation timestamp T:

1. The same-kind reference R is the most recent admitted swing of the candidate's kind in the current episode, strictly earlier than the candidate's confirmation timestamp.
2. The eligible supporting set consists of admitted opposite-kind swings in the same episode whose confirmation timestamps are strictly later than R's confirmation timestamp and strictly earlier than T.
3. If the eligible supporting set is empty, the candidate has incomplete opposite-kind evidence and remains unresolved under Section D, rule U1.
4. If the eligible supporting set contains one or more swings, the supporting opposite-kind swing is the member with the latest confirmation timestamp.
5. A swing that is unresolved or excluded is not eligible to serve as supporting evidence.
6. The selected supporting swing must be recorded in the candidate's ClassificationRecord using the field defined in Section G.

Whenever a supporting swing is selected, the engine emits:

`SUPPORTING_OPPOSITE_SELECTED:<candidate_swing_ts>:<supporting_swing_ts>`

This event applies to both bootstrap-supported and directionally classified support. It records evidence selection; it does not itself indicate admission.

The selection rule is deterministic. Given the same eligible candles, cutoff, and structural state, the same supporting swing must be selected.

## Section B — Same-kind reference and classification

1. Only admitted meaningful swings from the current episode may serve as same-kind references.
2. The candidate is classified against the most recent admitted same-kind swing in the current episode.
3. Classification follows the existing handbook definitions:
   - HIGH candidate:
     - HH when its high zone extends above the reference high zone.
     - LH when its high zone extends below the reference high zone.
     - EQ_HIGH when the zones overlap.
   - LOW candidate:
     - HL when its low zone extends above the reference low zone.
     - LL when its low zone extends below the reference low zone.
     - EQ_LOW when the zones overlap.
4. Bootstrap swings remain CLASSIFICATION_UNRESOLVED permanently within their episode. They do not acquire directional classifications later.
5. A bootstrap swing may serve as a same-kind reference for classifying a later candidate. Its own unresolved classification does not prevent the later candidate from receiving a directional classification.
6. Classification and admission are separate determinations. A candidate may have a directional classification but still remain unresolved or be excluded by the admission gate.

## Section C — Compatibility and bootstrap-support determination

The admission gate uses:
- candidate classification c;
- selected supporting opposite-kind swing;
- the supporting swing's classification s, where available.

### C1 — Bootstrap-support exception

If the selected supporting opposite-kind swing is the episode's Phase 1 bootstrap observation and its classification is CLASSIFICATION_UNRESOLVED, the bootstrap swing acts as an initial structural anchor, not as directional evidence.

Under this exception:
- A HIGH candidate is admitted if its own classification is HH or LH.
- A LOW candidate is admitted if its own classification is HL or LL.
- A candidate classified EQ_HIGH or EQ_LOW remains unresolved.

The exception applies only when the selected supporting swing is the episode's bootstrap observation.

It does not admit a candidate with an equal classification, does not admit a candidate without a selected supporting swing, and does not override the normal compatibility rules for directionally classified supporting swings.

### C2 — Equality under classified support

When the selected supporting swing has a directional classification, if either the candidate classification or supporting classification is EQ_HIGH or EQ_LOW, the pair provides no directional determination.

The candidate remains unresolved under Section D, rule U2.

### C3 — Directional admission pairs

When both candidate and supporting classifications are directional (HH, LH, HL, LL), the candidate is admitted if and only if the pair is one of:

| Candidate | Supporting swing | Outcome |
|---|---|---|
| HH | HL | Admitted — UPTREND extension |
| LH | LL | Admitted — DOWNTREND extension |
| HL | HH | Admitted — UPTREND continuation |
| LL | LH | Admitted — DOWNTRE continuation |

These pairs follow the handbook's established directional structural requirements.

No additional admission pair is introduced.

### C4 — Narrow exclusion pairs

The candidate is excluded if and only if the pair is:

| Candidate | Supporting swing | Outcome |
|---|---|---|
| HH | LL | Excluded |
| LL | HH | Excluded |

These are the only exclusion pairs.

### C5 — Other complete directional pairs

Any complete directional pair that is neither an admission pair nor one of the two exclusion pairs remains unresolved.

Examples include:
- (LH, HL)
- (HH, LH)
- (HL, LL)

No other pair is implicitly admitted or excluded.

### C6 — RANGE boundary

This admission gate does not introduce or modify a RANGE admission formula.

RANGE classification remains governed by the handbook's existing Section 9 requirements. A swing that does not satisfy a directional admission pair is not automatically admitted as a RANGE swing.

## Section D — Unresolved swings

A confirmed candidate swing remains unresolved for the current evaluation if any of the following applies:

- **U1 — Incomplete evidence:** no eligible admitted opposite-kind swing exists between the same-kind reference and candidate.
- **U2 — Equality under classified support:** the selected supporting swing has a directional classification, but either the candidate or supporting classification is EQ_HIGH or EQ_LOW.
- **U2a — Equality under bootstrap support:** the selected supporting swing is the episode's bootstrap observation, but the candidate classification is EQ_HIGH or EQ_LOW.
- **U3 — Non-extending complete pair:** both candidate and supporting classifications are directional, but the pair is neither an admission pair nor an exclusion pair.

The corresponding unresolved reason codes are fixed as follows:

| Rule | Reason code |
|---|---|
| U1 | `incomplete` |
| U2 | `eq_classified` |
| U2a | `bootstrap_equality` |
| U3 | `conflict` |

The Round 1 reason suffix `bootstrap` is retired for Round 2. A bootstrap observation is admitted as a Phase 1 anchor and does not emit an unresolved event. The reason code `bootstrap_equality` is reserved for U2a, where a candidate is unresolved because it is equal under bootstrap support.

An unresolved candidate:
- Is not admitted to the active structural sequence.
- Is not added to meaningful_highs or meaningful_lows.
- Is not added to excluded_swings.
- Emits `SWING_CONFIRMED_UNRESOLVED:<ts>:<reason_code>`.
- May be reconsidered at a later evaluation only as permitted by the existing Section 6 reconsideration rules.

The unresolved event describes the candidate's admission outcome. It must not be used merely because a bootstrap swing has an unresolved classification.

## Section E — Excluded swings

A candidate is excluded only when its complete directional pair matches one of the two exclusion pairs in Section C4.

An excluded swing:
- Is not admitted to the active structural sequence.
- Is not added to meaningful_highs or meaningful_lows.
- Is added to excluded_swings.
- Emits `SWING_EXCLUDED:<ts>:non_extending_incompatible`.
- Is not reinstated within the same episode under this version.

A swing must not appear as both admitted and excluded in the same episode.

A prior-episode excluded swing remains historical and auditable, but is not included in the current episode's excluded_swings.

## Section F — Episode boundaries

### F1 — Invalidation close

An episode boundary is established by a completed H1 candle that closes beyond the controlling level of an established regime, in accordance with the handbook's Section 8 invalidation rules.

The boundary is identified by the invalidation candle's close/confirmation timestamp, not its candle-open timestamp.

The invalidation candle must be completed. A wick beyond the controlling level does not establish an episode boundary.

### F2 — Most recent invalidation

For a given eligible H1 candle set and evaluation cutoff, identify the most recent completed H1 invalidation candle applicable under the existing Section 8 rules.

Its close/confirmation timestamp is the current episode boundary.

If no qualifying invalidation close exists in the eligible candle set, the evaluation belongs to the first episode and its episode boundary is None.

### F3 — Swing episode membership

A swing belongs to the new episode if and only if its confirmation timestamp is strictly later than the episode boundary.

A swing whose confirmation timestamp is at or before the invalidation close belongs to the prior episode.

The confirmation timestamp is the close/confirmation time of the right-hand candle that confirms the swing under the existing three-candle swing-confirmation rule.

The swing's timestamp_open remains its identity and chronological candle reference. It is not the timestamp used to assign episode membership.

This distinction ensures that a swing whose middle candle opened before an invalidation close, but whose confirmation occurred after that close, is assigned according to when the swing became confirmed.

### F4 — Prior-episode swings

Prior-episode swings:
- Remain historical and auditable in confirmed_swings and structural_events.
- Do not appear in current-episode meaningful_highs or meaningful_lows.
- Do not appear in current-episode excluded_swings.
- Do not serve as same-kind references or opposite-kind supporting evidence for current-episode candidates.

### F5 — Bootstrap per episode

Each episode has its own Phase 1 bootstrap observations.

The first confirmed HIGH and first confirmed LOW in the episode are admitted as bootstrap observations under Amendment 05.

Each bootstrap observation:
- Has is_bootstrap=True.
- Has classification=CLASSIFICATION_UNRESOLVED.
- Remains classification-unresolved for the duration of that episode.

The bootstrap-support exception in Section C1 applies only to the episode's bootstrap observation.

### F6 — Determinism

Given the same eligible H1 candles and evaluation cutoff, the episode boundary, swing episode membership, bootstrap observations, reference selection, supporting-swing selection, and admission outcomes must be deterministic.

Re-evaluation with identical inputs must produce identical results.

## Section G — State representation and audit events

### G1 — Excluded swings

MarketStructureState gains:

`excluded_swings: tuple[SwingPoint, ...] = ()`

Excluded swings are ordered by timestamp_open ascending.

A swing must not appear in both:
- meaningful_highs or meaningful_lows; and
- excluded_swings

within the same episode.

A swing that remains unresolved must not appear in excluded_swings.

### G2 — Supporting evidence in ClassificationRecord

ClassificationRecord gains:

`supporting_opposite_swing: SwingPoint | None = None`

This field records the exact selected opposite-kind swing used by the admission gate.

- For an admitted non-bootstrap candidate, it identifies the supporting swing.
- For an excluded candidate, it identifies the supporting swing.
- For an unresolved candidate with a selected support, it identifies that support.
- For a bootstrap observation, it is None.
- For a candidate with incomplete evidence, it is None.

The field stores the selected swing itself, not merely its timestamp or classification. This preserves the evidence needed for downstream inspection and audit.

### G3 — Classification and admission are distinct

A bootstrap swing is admitted even though its classification is CLASSIFICATION_UNRESOLVED.

Its record must therefore distinguish:
- is_bootstrap=True;
- classification=CLASSIFICATION_UNRESOLVED;
- admitted Phase 1 status.

The engine emits:

`SWING_MEANINGFUL_PHASE1:<ts>`

for a bootstrap observation.

It does not emit `SWING_CONFIRMED_UNRESOLVED:<ts>:bootstrap` for that observation. That unresolved event is reserved for a candidate whose admission outcome is unresolved. The Round 1 `:bootstrap` reason suffix is retired; the only bootstrap-related unresolved candidate reason in Round 2 is `:bootstrap_equality` under U2a.

### G4 — Supporting-swing selection event

Whenever a supporting swing is selected, including bootstrap support, emit:

`SUPPORTING_OPPOSITE_SELECTED:<candidate_swing_ts>:<supporting_swing_ts>`

This event records the selected evidence and does not indicate that the candidate was admitted.

### G5 — Admission and exclusion events

- Bootstrap admission: `SWING_MEANINGFUL_PHASE1:<ts>`
- Directional admission: use the existing meaningful-swing admission event defined by the canonical specification.
- Unresolved candidate: `SWING_CONFIRMED_UNRESOLVED:<ts>:<reason_code>`
- Excluded candidate: `SWING_EXCLUDED:<ts>:non_extending_incompatible`

No candidate may emit both an admission event and an exclusion event for the same episode evaluation.

## Section H — Round 1 to Round 2 compatibility

This amendment preserves:
- Existing SwingClassification enum members.
- Existing Phase 1 bootstrap admission behavior.
- Existing three-candle candidate confirmation.
- Existing same-kind reference semantics: most recent admitted same-kind swing.
- Existing UPTREND and DOWNTREND requirements.
- Existing RANGE classification rules.

Round 2 implementation must add:
- Supporting opposite-kind swing selection under Section A.
- Explicit supporting_opposite_swing on ClassificationRecord.
- Bootstrap-support exception under Section C1.
- Admission, exclusion, and unresolved outcomes under Sections C-E.
- excluded_swings on MarketStructureState.
- Episode boundary and membership handling under Section F.
- The audit-event semantics defined in Section G.

Round 2 is expected to change the private `_meaningful_swings` implementation signature so the episode boundary can be supplied or derived from the eligible evaluation context. The exact private method signature is an implementation detail to be specified during the Round 2 design. This anticipated private-signature change is not a deviation from the amendment. The public H1 evaluation contract remains based on eligible H1 candles and an explicit evaluation cutoff.

No new RANGE admission combinations may be introduced.

## Section I — Worked examples

All timestamps below represent swing confirmation order unless explicitly stated otherwise. Price values are illustrative fixture values. The examples assume valid confirmed swings and source zones under the existing handbook rules.

### Example 1 — First directional admission using bootstrap support

Fixture:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t1 | HIGH | 1.0800 | Bootstrap HIGH |
| t2 | LOW | 1.0600 | Bootstrap LOW |
| t3 | HIGH | 1.0900 | Candidate |

Evaluation of t3:
- Same-kind reference: HIGH t1.
- Intervening opposite-kind swing: LOW t2.
- Selected support: LOW t2, the bootstrap LOW.
- Candidate classification: HH.
- Bootstrap support + directional HIGH classification → admitted.

Expected outcome:
- HIGH t3 is admitted.
- Its record has classification=HH, is_bootstrap=False, and supporting_opposite_swing=LOW t2.
- `SUPPORTING_OPPOSITE_SELECTED:t3:t2` is emitted.
- No unresolved or exclusion event is emitted for t3.

### Example 2 — Subsequent admission using classified support

Fixture:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t1 | HIGH | 1.0800 | Bootstrap HIGH |
| t2 | LOW | 1.0600 | Bootstrap LOW |
| t3 | HIGH | 1.0900 | Admitted HH |
| t4 | LOW | 1.0700 | Candidate |

Evaluation of t4:
- Same-kind reference: LOW t2.
- Intervening opposite-kind swing: HIGH t3.
- Selected support: HIGH t3, classified HH.
- Candidate classification: HL.
- Pair (HL, HH) → admitted.

Expected outcome:
- LOW t4 is admitted.
- Its record has classification=HL, is_bootstrap=False, and supporting_opposite_swing=HIGH t3.
- `SUPPORTING_OPPOSITE_SELECTED:t4:t3` is emitted.

### Example 3 — Narrow exclusion using classified support

Fixture:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t1 | HIGH | 1.0800 | Bootstrap HIGH |
| t2 | LOW | 1.0600 | Bootstrap LOW |
| t3 | HIGH | 1.0900 | Admitted HH |
| t4 | LOW | 1.0400 | Candidate |

Evaluation of t4:
- Same-kind reference: LOW t2.
- Intervening opposite-kind swing: HIGH t3.
- Selected support: HIGH t3, classified HH.
- Candidate classification: LL.
- Pair (LL, HH) → excluded.

Expected outcome:
- LOW t4 is excluded.
- It appears in excluded_swings.
- It does not appear in meaningful_lows.
- `SUPPORTING_OPPOSITE_SELECTED:t4:t3` is emitted.
- `SWING_EXCLUDED:t4:non_extending_incompatible` is emitted.

### Example 4 — Equality under bootstrap support remains unresolved

Fixture:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t1 | HIGH | 1.0800 | Bootstrap HIGH |
| t2 | LOW | 1.0600 | Bootstrap LOW |
| t3 | HIGH | 1.0800 | Candidate |

Evaluation of t3:
- Same-kind reference: HIGH t1.
- Selected opposite-kind support: LOW t2, bootstrap.
- Candidate classification: EQ_HIGH.
- Bootstrap support does not admit an equal candidate.

Expected outcome:
- HIGH t3 remains unresolved.
- It does not appear in meaningful_highs or excluded_swings.
- `SUPPORTING_OPPOSITE_SELECTED:t3:t2` is emitted.
- `SWING_CONFIRMED_UNRESOLVED:t3:bootstrap_equality` is emitted.

### Example 5 — Episode reset following confirmed invalidation

Fixture:

Episode 1:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t1 | HIGH | 1.0800 | Bootstrap HIGH |
| t2 | LOW | 1.0600 | Bootstrap LOW |
| t3 | HIGH | 1.0900 | Admitted HH |
| t4 | LOW | 1.0700 | Admitted HL |

A completed H1 candle subsequently closes below the controlling HL at 1.0700. Its candle-open timestamp is i_open; its close/confirmation timestamp is i_close.

Episode 2:

| Swing | Kind | Price | Status |
|---|---|---:|---|
| t5 | HIGH | 1.0750 | Bootstrap HIGH |
| t6 | LOW | 1.0550 | Bootstrap LOW |

Both t5 and t6 have confirmation timestamps strictly later than i_close.

Expected outcome:
- The invalidation close establishes the Episode 2 boundary at i_close.
- Episode 1 swings remain historical and auditable.
- Episode 1 swings do not serve as references or support for Episode 2.
- HIGH t5 and LOW t6 are admitted as Episode 2 bootstrap observations.
- Both remain CLASSIFICATION_UNRESOLVED permanently within Episode 2.
- Each has is_bootstrap=True and no supporting_opposite_swing.
- Each emits `SWING_MEANINGFUL_PHASE1:<ts>`.
- Neither emits `SWING_CONFIRMED_UNRESOLVED:<ts>:bootstrap`.

A swing whose confirmation timestamp is at or before i_close belongs to Episode 1, even if its middle candle's timestamp_open precedes or overlaps the invalidation candle.

## Section J — Change control and implementation hold

This amendment is documentation-only. It does not authorize implementation or test changes in the same change.

The following contract questions are resolved in this amendment and must not be deferred to implementation:

- Supporting-swing selection: Section A.
- Same-kind reference selection: Section B.
- Bootstrap-support behavior: Section C1.
- EQ behavior: Sections C2 and D.
- Directional admission pairs: Section C3.
- Narrow exclusion pairs: Section C4.
- Other complete pairs: Section C5.
- RANGE boundary: Section C6.
- Excluded swing representation: Section G1.
- Supporting evidence representation: Section G2.
- Bootstrap admission and audit events: Section G3.
- Supporting-swing selection event: Section G4.
- Episode boundary and membership: Section F.
- Unresolved reason-code mapping and retirement of the Round 1 `:bootstrap` suffix: Section D.
- Private `_meaningful_swings` signature allowance: Section H.

Round 2 implementation remains on hold until this complete amendment is reviewed and frozen.

No implementation may introduce additional admission pairs, exclusion pairs, RANGE admission rules, tolerance thresholds, or episode rules beyond this amendment and the existing canonical handbook.

## Final review notes

The amendment preserves Decision A: the most recent admitted same-kind swing remains the reference, and the most recent admitted opposite-kind swing strictly between that reference and the candidate is selected as support. No new rule preserves an older reference when another same-kind swing is admitted.

The possibility of multiple eligible intervening opposite-kind swings is handled by the deterministic latest-confirmation selection rule in Section A. The worked examples do not claim that multiple intervening supports are unreachable and do not add a separate special-case rule.

The amendment explicitly adds `supporting_opposite_swing: SwingPoint | None` to ClassificationRecord. This is an intentional schema change, not an implementation detail left open.
