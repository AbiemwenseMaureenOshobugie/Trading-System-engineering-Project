# MS-0.1A Clarification Amendment 08 — Chronological Episode Replay and Invalidation Ordering

**Status:** Documentation-only clarification. No implementation or test files are changed by this amendment.
**Canonical target:** `docs/strategy/ms-0.1a-market-structure-spec.md`
**Related amendments:** 04, 05, 06, 07.

## Purpose

Amendment 07 defines episode membership using the confirmation timestamp of a completed H1 invalidation candle. This amendment clarifies how the episode boundary is derived without creating a circular dependency between swing admission, regime establishment and invalidation detection.

The H1 engine shall derive structural episodes through chronological replay of eligible completed H1 candles and confirmed swing events.

The replay shall preserve the existing handbook definitions of:

- Confirmed swing candidates.
- Meaningful swing admission.
- Unresolved and excluded swings.
- Established UPTREND and DOWNTREND regimes.
- Controlling-swing selection.
- Completed-candle invalidation.
- Episode membership and Phase 1 bootstrap observations.

This amendment does not introduce new directional admission pairs, exclusion pairs, structural thresholds, invalidation thresholds or RANGE rules.

## Section A — Chronological evaluation

1. Eligible H1 candles shall be processed in chronological order by their completed-candle timestamps.

2. Confirmed swing events shall retain their confirmation timestamps as defined by Amendment 07.

3. The engine shall maintain an episode-local structural state containing the admitted meaningful swings, their classifications, their supporting evidence and the applicable bootstrap observations.

4. The episode-local structural state shall be updated as confirmed swings become available.

5. The engine shall not use a swing to establish a regime or controlling level before that swing's confirmation timestamp. For same-close cases where a swing's confirmation timestamp equals the candidate invalidation candle's close, Section D governs.

6. Unresolved and excluded swings shall remain available for their required historical and audit representations but shall not serve as same-kind references, opposite-kind supporting evidence or regime-establishment evidence.

## Section B — Regime establishment during replay

1. At each completed H1 candle close, the engine shall determine whether the currently active episode has established a directional regime.

2. Regime establishment shall use only admitted meaningful swings belonging to that episode.

3. The existing handbook requirements remain unchanged: UPTREND requires at least two HH and two HL relationships. DOWNTREND requires at least two LH and two LL relationships.

4. Relationship classifications shall be calculated using the admitted meaningful swings of the current episode, following the existing specification and Amendment 07 admission rules.

5. Confirmed-but-unresolved and excluded swings shall not contribute to the directional establishment counts.

6. The controlling swing shall be selected using the existing handbook and Amendment 04 rules, from the admitted meaningful swings of the current episode.

## Section C — Invalidation evaluation and ordering

1. A completed H1 candle close shall be evaluated against the controlling swing of the established regime that existed immediately before that close.

2. UPTREND is invalidated when a completed H1 candle closes below its controlling HL.

3. DOWNTREND is invalidated when a completed H1 candle closes above its controlling LH.

4. A wick beyond the controlling level does not establish invalidation.

5. The invalidation decision shall use the episode-local structural state available before the candidate invalidation candle closes.

6. A swing that becomes confirmed at the same timestamp as the candidate invalidation close shall not influence the invalidation decision at that close.

7. When invalidation is confirmed, the invalidation candle's close timestamp establishes the episode boundary.

8. The invalidation candle belongs to the episode that it invalidates.

9. A new episode begins after the invalidation close. Its admission state, same-kind references, opposite-kind supporting evidence and Phase 1 bootstrap observations are independent of those of the previous episode.

## Section D — Same-close confirmation ordering

1. Swing confirmation and H1 invalidation may occur at the same completed-candle timestamp.

2. The invalidation decision shall be evaluated first using the structural state accumulated strictly before that timestamp.

3. Confirmed swings with that same confirmation timestamp shall not be used to prevent, reverse or otherwise alter the invalidation decision.

4. Same-close confirmed swings shall be assigned to the episode ending at that invalidation close, in accordance with Amendment 07 §F3.

5. They shall not become active references, supporting evidence or regime-establishment evidence in the replacement episode.

6. When no invalidation occurs at the candle close, confirmed swings at that timestamp may be processed into the current episode using the Amendment 07 admission gate.

## Section E — Episode membership and timestamp semantics

1. The episode boundary is the close/confirmation timestamp of the invalidation candle.

2. A confirmed swing belongs to a replacement episode if and only if `swing.confirmed_at > episode_start`.

3. A confirmed swing whose confirmation timestamp is at or before the episode boundary belongs to the preceding episode.

4. For the first episode, where `episode_start` is `None`, all confirmed swings available by the first episode's ending boundary belong to that episode. If no invalidation boundary occurs within the evaluation history, all confirmed swings available by the evaluation cutoff belong to the first episode.

5. Throughout Sections B–G, wherever a confirmed swing's chronological position in the replay is referenced, the relevant timestamp is its `confirmed_at` timestamp.

6. Wherever a swing's identity or originating candle is referenced, the relevant timestamp is its `timestamp_open`, represented by `SwingPoint.timestamp`.

7. The distinction is intentional:
   - `timestamp_open` identifies the swing's originating middle candle.
   - `confirmed_at` identifies when the swing became available for admission, classification, supporting-swing selection and episode membership.

8. The swing's middle-candle opening timestamp shall not replace its confirmation timestamp for chronological replay, admission ordering or episode membership.

9. Prior-episode swings remain historical and auditable but shall not serve as references, supporting evidence or directional establishment evidence in a replacement episode.

## Section F — Episode-local admission

1. Each episode shall have its own admission sequence.

2. The first confirmed HIGH and first confirmed LOW admitted within an episode shall follow the Phase 1 bootstrap rules established by Amendment 05.

3. The same-kind reference and supporting opposite-kind swing shall be selected only from admitted swings within the current episode, as specified by Amendment 07.

4. Unresolved swings shall not become admission references or supporting evidence.

5. Excluded swings shall not become admission references or supporting evidence.

6. Admission outcomes shall not be retroactively changed because a later episode begins.

7. The existing reconsideration rules for unresolved swings remain unchanged within their applicable episode.

8. Whenever the engine selects a supporting opposite-kind swing for a candidate, it shall emit:

   `SUPPORTING_OPPOSITE_SELECTED:<candidate_swing_ts>:<supporting_swing_ts>`

   This applies both when the selected support is the episode's Phase 1 bootstrap observation and when it is a directionally classified admitted swing.

9. The supporting-selection event shall be emitted immediately upon selection and before evaluating compatibility. It records the evidence selection itself, independently of whether the candidate is subsequently admitted, excluded or left unresolved.

10. The event's swing timestamps identify the originating swing candles. They do not replace confirmation timestamps for replay ordering or episode membership.

## Section G — Repeated invalidation

1. Each established directional regime shall be evaluated against subsequent completed H1 candle closes.

2. When a later completed close invalidates the current episode's controlling swing, that close establishes another episode boundary.

3. Each replacement episode shall independently accumulate its own admitted swings and establish its own directional regime.

4. A previous episode's controlling swing shall not remain active after its invalidation.

5. A replacement regime shall not be established merely because the previous regime was invalidated. It must independently satisfy the existing directional establishment requirements.

## Section H — Determinism and replay consistency

1. Given the same eligible H1 candles and evaluation cutoff, chronological replay shall produce the same:
   - Confirmed swing history.
   - Episode boundaries.
   - Episode membership.
   - Admission, unresolved and exclusion outcomes.
   - Supporting-swing selections.
   - Relationship classifications.
   - Controlling-swing selections.
   - Final market-structure state.
   - Structural audit events.

2. Re-evaluation with identical inputs shall produce identical results.

3. An evaluation using a later cutoff shall preserve the historical episode boundaries, admission outcomes, classifications and audit events determined by the earlier eligible candle sequence, provided that the later eligible candle sequence is a strict prefix-extension of the earlier one. All decisions already determined by that earlier eligible sequence shall repeat identically in the later evaluation.

4. A strict prefix-extension of the eligible candle sequence means that the earlier eligible sequence (as produced by `_eligible_candles` for the earlier cutoff) is unchanged and the later eligible sequence only appends additional completed candles. If any eligible candle in the earlier sequence is revised, replaced or removed, the prefix-extension guarantee does not apply. The guarantee concerns the eligible sequence after cutoff filtering, not the raw `candles` argument.

## Section I — Scope

This amendment clarifies the derivation and ordering of existing handbook rules.

It does not:

- Admit confirmed-but-excluded or unresolved swings into directional establishment.
- Introduce a separate regime-establishment definition for invalidation detection.
- Infer episode boundaries from unadmitted evidence.
- Introduce a two-pass approximation.
- Introduce a new swing-confirmation algorithm.
- Change the existing UPTREND, DOWNTREND or RANGE requirements.
- Treat a wick as an invalidation.
- Allow a same-close swing confirmation to influence the invalidation decision at that close.
- Change the public H1 evaluation contract.

The amendment is documentation-only. Implementation and tests remain on hold until the amendment is reviewed and frozen.

## Section J — Change control

This amendment changes documentation only. It does not authorize implementation or test changes in the same change.

The following contract questions are resolved in this amendment and must not be deferred to implementation:

- Chronological replay ordering: Sections A and D.
- Regime establishment from admitted evidence only: Section B.
- Invalidation evaluation against pre-close state: Section C.
- Same-close confirmation ordering: Section D.
- Episode membership and timestamp semantics: Section E.
- Episode-local admission including bootstrap and audit event: Section F.
- Repeated invalidation and per-episode independence: Section G.
- Determinism and strict prefix-extension consistency: Section H.

Phase B Round 2B implementation remains on hold until this complete amendment is reviewed and frozen.

No implementation may introduce additional episode-boundary derivation rules, admit unadmitted evidence into regime establishment, or use a two-pass approximation in place of the chronological replay specified here.
