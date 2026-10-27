"""Tests for the deterministic MS-0.1A H1 market-structure engine."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from trading_system.domain import MarketCandle, PriceZone, Regime, SwingKind, Timeframe
from trading_system.strategy.market_structure import H1MarketStructureEngine
from trading_system.strategy.market_structure.engine import _Candidate, _Confirmed

UTC = timezone.utc


def candle(i: int, open_: str, high: str, low: str, close: str) -> MarketCandle:
    start = datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=i)
    return MarketCandle(
        symbol="EURUSD",
        timeframe=Timeframe.H1,
        timestamp_open=start,
        timestamp_close=start + timedelta(hours=1),
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
    )


def confirmed(i: int, kind: SwingKind, price: str) -> _Confirmed:
    if kind is SwingKind.HIGH:
        c = candle(i, price, price, "1.0000", price)
    else:
        c = candle(i, price, "1.1000", price, price)
    return _Confirmed(_Candidate(i, kind, c), c.timestamp_close)


def test_empty_history_is_initial_unclear() -> None:
    state = H1MarketStructureEngine().evaluate(
        candles=[],
        evaluation_cutoff=datetime(2026, 1, 2, tzinfo=UTC),
    )
    assert state.regime is Regime.UNCLEAR
    assert "INITIAL_UNCLEAR_INSUFFICIENT_HISTORY" in state.structural_events


def test_dual_candidate_is_rejected() -> None:
    candles = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0900", "1.1000"),
        candle(2, "1.1000", "1.1050", "1.0950", "1.1000"),
    ]
    state = H1MarketStructureEngine().evaluate(
        candles=candles,
        evaluation_cutoff=candles[-1].timestamp_close,
    )
    assert state.meaningful_highs == ()
    assert state.meaningful_lows == ()
    assert any(event.startswith("DUAL_CANDIDATE_REJECTED:") for event in state.structural_events)


def test_cutoff_excludes_later_candles() -> None:
    early = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0980", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    ]
    later = early + [
        candle(3, "1.1020", "1.1200", "1.1000", "1.1180"),
        candle(4, "1.1180", "1.1190", "1.0900", "1.0920"),
    ]
    engine = H1MarketStructureEngine()
    cutoff = early[-1].timestamp_close
    assert engine.evaluate(candles=later, evaluation_cutoff=cutoff) == engine.evaluate(
        candles=early, evaluation_cutoff=cutoff
    )


def test_t19_bounding_pair_uses_actual_price_bounds_not_chronology() -> None:
    highs = [
        confirmed(1, SwingKind.HIGH, "1.1200"),
        confirmed(5, SwingKind.HIGH, "1.1100"),
        confirmed(9, SwingKind.HIGH, "1.1300"),
    ]
    lows = [
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(10, SwingKind.LOW, "1.0950"),
    ]
    upper, lower = H1MarketStructureEngine._bounding_pair(highs, lows)
    assert upper == PriceZone(Decimal("1.1300"), Decimal("1.1300"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0800"))


def test_t20_state_exposes_explicit_boundary_fields() -> None:
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    lower = PriceZone(Decimal("1.0800"), Decimal("1.0850"))
    state = H1MarketStructureEngine._state(
        Regime.RANGE, (), (), None, upper, lower, (), datetime(2026, 1, 2, tzinfo=UTC)
    )
    assert state.range_upper_boundary == upper
    assert state.range_lower_boundary == lower


def test_t21_boundary_values_are_not_mutated_by_reaction_evaluation() -> None:
    upper = PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    lower = PriceZone(Decimal("1.0800"), Decimal("1.0850"))
    meaningful = [
        confirmed(1, SwingKind.HIGH, "1.1230"),
        confirmed(2, SwingKind.LOW, "1.0830"),
        confirmed(3, SwingKind.HIGH, "1.1240"),
    ]
    H1MarketStructureEngine()._range_reactions(meaningful, upper, lower)
    assert upper == PriceZone(Decimal("1.1200"), Decimal("1.1250"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0850"))


def test_t22_alternating_reactions_can_start_from_either_side() -> None:
    t = datetime(2026, 1, 1, tzinfo=UTC)
    assert H1MarketStructureEngine._alternates(
        [t, t + timedelta(hours=2)],
        [t + timedelta(hours=1), t + timedelta(hours=3)],
    )
    assert H1MarketStructureEngine._alternates(
        [t + timedelta(hours=1), t + timedelta(hours=3)],
        [t, t + timedelta(hours=2)],
    )


def test_t23_earlier_non_bounding_swing_is_not_selected() -> None:
    highs = [
        confirmed(1, SwingKind.HIGH, "1.1150"),
        confirmed(4, SwingKind.HIGH, "1.1200"),
        confirmed(7, SwingKind.HIGH, "1.1180"),
    ]
    lows = [
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(5, SwingKind.LOW, "1.0800"),
        confirmed(8, SwingKind.LOW, "1.0850"),
    ]
    upper, lower = H1MarketStructureEngine._bounding_pair(highs, lows)
    assert upper == PriceZone(Decimal("1.1200"), Decimal("1.1200"))
    assert lower == PriceZone(Decimal("1.0800"), Decimal("1.0800"))


def test_t24_later_candidates_cannot_change_an_earlier_cutoff_state() -> None:
    base = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.0980", "1.1080"),
        candle(2, "1.1080", "1.1090", "1.1000", "1.1020"),
    ]
    extended = base + [
        candle(3, "1.1020", "1.1300", "1.1000", "1.1250"),
        candle(4, "1.1250", "1.1260", "1.0750", "1.0800"),
    ]
    cutoff = base[-1].timestamp_close
    engine = H1MarketStructureEngine()
    assert engine.evaluate(candles=extended, evaluation_cutoff=cutoff) == engine.evaluate(
        candles=base, evaluation_cutoff=cutoff
    )


def test_candidate_zones_use_ordered_body_to_extreme_boundaries() -> None:
    high_candle = candle(20, "1.1000", "1.1100", "1.0950", "1.1050")
    low_candle = candle(21, "1.1000", "1.1050", "1.0900", "1.0950")
    high = _Candidate(20, SwingKind.HIGH, high_candle)
    low = _Candidate(21, SwingKind.LOW, low_candle)
    assert high.zone == PriceZone(Decimal("1.1050"), Decimal("1.1100"))
    assert low.zone == PriceZone(Decimal("1.0900"), Decimal("1.0950"))


def test_r56_replacement_downtrend_established_after_uptrend_invalidation_is_not_transition() -> None:
    # MS-0.1A §8: "`TRANSITION` exists only after an established regime is invalidated/structurally
    # changed and a replacement regime is not yet established."
    engine = H1MarketStructureEngine()
    swings = [
    # Prior episode (UPTREND)
    confirmed(1, SwingKind.HIGH, "1.0800"),
    confirmed(2, SwingKind.LOW,  "1.0600"),
    confirmed(3, SwingKind.HIGH, "1.0900"),
    confirmed(4, SwingKind.LOW,  "1.0700"),
    confirmed(5, SwingKind.HIGH, "1.1000"),
    confirmed(6, SwingKind.LOW,  "1.0800"),
    confirmed(7, SwingKind.HIGH, "1.1100"),
    confirmed(8, SwingKind.LOW,  "1.0900"),  # controlling HL, to be invalidated
    # Replacement episode (must establish DOWNTREND on its own)
    confirmed(10, SwingKind.HIGH, "1.1000"),  # 1st HIGH in episode, no label
    confirmed(11, SwingKind.LOW,  "1.0850"),  # 1st LOW in episode, no label
    confirmed(12, SwingKind.HIGH, "1.0950"),  # LH vs 1.1000
    confirmed(13, SwingKind.LOW,  "1.0800"),  # LL vs 1.0850
    confirmed(14, SwingKind.HIGH, "1.0900"),  # LH vs 1.0950
    confirmed(15, SwingKind.LOW,  "1.0750"),  # LL vs 1.0800
]
    labels = engine._relationship_labels(swings)
    assert list(labels.values()).count("LH") >= 2  # precondition: replacement DOWNTREND evidence
    assert list(labels.values()).count("LL") >= 2
    # Precondition: the post-invalidation episode (hours 10-15) contains
    # at least 2 LH + 2 LL on its own, so DOWNTREND can establish from
    # episode-scoped evidence alone.
    episode_start_ts = swings[8].swing.timestamp  # first post-invalidation swing (hour 10)
    episode_swings = [x for x in swings if x.swing.timestamp >= episode_start_ts]
    episode_labels = engine._relationship_labels(episode_swings)
    assert list(episode_labels.values()).count("LH") >= 2, (
        f"episode-scoped labels must contain 2 LH; got {list(episode_labels.values())}"
    )
    assert list(episode_labels.values()).count("LL") >= 2, (
        f"episode-scoped labels must contain 2 LL; got {list(episode_labels.values())}"
    )
    # Completed close 1.0850 below old controlling HL 1.0900 (before the LH/LL swings),
    # and no close above controlling LH 1.0950 afterwards.
    invalidation = [candle(9, "1.0900", "1.0910", "1.0840", "1.0850")]
    regime, controlling, _, _ = engine._classify(invalidation, swings, labels, [])
    assert regime is Regime.DOWNTREND, (
        f"old UPTREND invalidated by close 1.0850 < HL 1.0900; replacement DOWNTREND "
        f"(LH 1.1000/1.0950, LL 1.0850/1.0800, controlling LH 1.0950) is established, "
        f"so TRANSITION must not be reported; regime was {regime}"
    )
    assert controlling == swings[12].swing


def test_r57_invalidated_structure_is_non_controlling_in_transition() -> None:
    # MS-0.1A §8: "Invalidated structure remains historical but becomes inactive and non-controlling."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW, "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(7, SwingKind.HIGH, "1.1100"),
        confirmed(8, SwingKind.LOW, "1.0900"),  # controlling HL, about to be invalidated
    ]
    labels = engine._relationship_labels(swings)
    invalidation = [candle(9, "1.0900", "1.0910", "1.0840", "1.0850")]
    regime, controlling, _, _ = engine._classify(invalidation, swings, labels, [])
    assert regime is Regime.TRANSITION  # precondition: no replacement swings exist yet
    assert controlling != swings[-1].swing, (
        f"HL {swings[-1].swing.price} was invalidated by close 1.0850 and must be "
        f"non-controlling, but controlling_level is still {controlling}"
    )


def test_r59_no_range_breakout_recorded_while_trend_is_established() -> None:
    # MS-0.1A §9 condition 5: "no sustained directional progression sufficient for UPTREND or DOWNTREND."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW, "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW, "1.0800"),
        confirmed(7, SwingKind.HIGH, "1.1100"),
        confirmed(8, SwingKind.LOW, "1.0900"),
    ]
    labels = engine._relationship_labels(swings)
    assert list(labels.values()).count("HH") >= 2  # precondition: trend sufficient
    assert list(labels.values()).count("HL") >= 2
    events: list[str] = []
    later = [candle(20, "1.1100", "1.1160", "1.1090", "1.1150")]
    regime, _, _, _ = engine._classify(later, swings, labels, events)
    breakouts = [e for e in events if e.startswith("RANGE_BREAKOUT")]
    assert not breakouts, (
        f"HH 1.0900/1.1000/1.1100 and HL 1.0700/1.0800/1.0900 are sufficient for UPTREND, "
        f"so no valid range exists and no range breakout may be recorded; got {breakouts}"
    )
    assert regime is not Regime.RANGE


def test_r65_range_penetration_is_decided_by_next_completed_candle() -> None:
    # MS-0.1A §9: a penetration is a completed close "on or past the outer edge of the boundary zone,
    # inclusive"; "The immediately following H1 candle determines whether that penetration failed or
    # was confirmed"; no following candle -> "provisional"; a following close beyond the opposite
    # boundary fails the original penetration and starts a separate opposite-direction evaluation;
    # "'Immediately following' means the next completed candle in the evaluated sequence; gaps in
    # market time do not affect the rule."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.1100"),
        confirmed(2, SwingKind.LOW, "1.0900"),
        confirmed(3, SwingKind.HIGH, "1.1100"),
        confirmed(4, SwingKind.LOW, "1.0900"),
    ]  # upper boundary 1.1100, lower boundary 1.0900, alternating, no trend
    labels = engine._relationship_labels(swings)

    def at(i: int, close: str) -> MarketCandle:
        value = Decimal(close)
        return candle(i, close, str(value + Decimal("0.0005")), str(value - Decimal("0.0005")), close)

    cases = [
        ("confirmed: 1.1150 then 1.1180 (precondition)", [at(6, "1.1150"), at(7, "1.1180")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
        ("failed: 1.1150 then inside 1.1050", [at(6, "1.1150"), at(7, "1.1050")], Regime.RANGE, None),
        ("inclusive upper edge: 1.1100 then 1.1100", [at(6, "1.1100"), at(7, "1.1100")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
        ("inclusive lower edge: 1.0900 then 1.0900", [at(6, "1.0900"), at(7, "1.0900")], Regime.TRANSITION, "RANGE_BREAKOUT_DOWN"),
        ("provisional: 1.1150 with no following candle", [at(6, "1.1150")], Regime.RANGE, None),
        ("opposite: 1.1150 then beyond lower 1.0850 (opposite provisional)", [at(6, "1.1150"), at(7, "1.0850")], Regime.RANGE, None),
        ("opposite confirmed separately: 1.1150, 1.0850, 1.0800", [at(6, "1.1150"), at(7, "1.0850"), at(8, "1.0800")], Regime.TRANSITION, "RANGE_BREAKOUT_DOWN"),
        ("gap, inside: 1.1150 then 1.1050 twenty-four hours later", [at(6, "1.1150"), at(30, "1.1050")], Regime.RANGE, None),
        ("gap, beyond: 1.1150 then 1.1180 twenty-four hours later (precondition)", [at(6, "1.1150"), at(30, "1.1180")], Regime.TRANSITION, "RANGE_BREAKOUT_UP"),
    ]
    divergences = []
    for name, candles, expected_regime, expected_event in cases:
        events: list[str] = []
        regime, _, _, _ = engine._classify(candles, swings, labels, events)
        breakouts = [e for e in events if e.startswith("RANGE_BREAKOUT")]
        expected_events = [expected_event] if expected_event else []
        if regime is not expected_regime or breakouts != expected_events:
            divergences.append(
                f"{name}: expected {expected_regime.name} {expected_events}, "
                f"got {regime.name} {breakouts}"
            )
    assert not divergences, (
        f"{len(divergences)} of {len(cases)} MS-0.1A §9 penetration cases diverge "
        f"(upper 1.1100 / lower 1.0900): " + " | ".join(divergences)
    )


def test_r68_established_uptrend_persists_after_close_above_last_swing_high() -> None:
    # MS-0.1A §10: "An established regime persists while its defining conditions remain valid."
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW, "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),  # HH
        confirmed(4, SwingKind.LOW, "1.0700"),  # HL
        confirmed(5, SwingKind.HIGH, "1.1000"),  # HH
        confirmed(6, SwingKind.LOW, "1.0800"),  # HL
        confirmed(7, SwingKind.HIGH, "1.1100"),  # HH
        confirmed(8, SwingKind.LOW, "1.0900"),  # HL, controlling
    ]
    labels = engine._relationship_labels(swings)
    before, _, _, _ = engine._classify([], swings, labels, [])
    assert before is Regime.UPTREND  # precondition: 3 HH, 3 HL, controlling HL intact

    # One later close above the last swing high; no close below controlling HL 1.0900.
    later = [candle(20, "1.1100", "1.1160", "1.1090", "1.1150")]
    regime, controlling, _, _ = engine._classify(later, swings, labels, [])
    assert regime is Regime.UPTREND, (
        f"UPTREND (HH 1.0900/1.1000/1.1100, HL 1.0700/1.0800/1.0900, controlling HL "
        f"{swings[-1].swing.price}) must persist; a close of 1.1150 above last HH 1.1100 "
        f"does not break the controlling HL, but regime was {regime}"
    )
    assert controlling == swings[-1].swing

def test_t1_controlling_swing_moves_to_new_same_kind_swing() -> None:
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    labels = engine._relationship_labels(swings)
    _, before, _, _ = engine._classify([], swings, labels, [])
    assert before == swings[5].swing

    swings.append(confirmed(7, SwingKind.LOW, "1.0900"))
    labels = engine._relationship_labels(swings)
    _, after, _, _ = engine._classify([], swings, labels, [])
    assert after == swings[6].swing, (
        f"new HL {swings[6].swing.price} should become controlling; got {after}"
    )

def test_t2_controlling_swing_cleared_when_invalidated() -> None:
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    labels = engine._relationship_labels(swings)
    invalidation = [candle(7, "1.0800", "1.0810", "1.0750", "1.0760")]
    regime, controlling, _, _ = engine._classify(invalidation, swings, labels, [])
    assert regime is Regime.TRANSITION
    assert controlling is None, (
        f"invalidated HL {swings[5].swing.price} must not be controlling; got {controlling}"
    )

def test_t3_post_invalidation_episode_only_counts_new_swings() -> None:
    # MS-0.1A §8 / invariant 33: "A transition episode contains only swings
    # confirmed after the invalidating close; prior-episode swings do not
    # count toward later establishment."
    #
    # Fixture:
    #   - Prior UPTREND episode: 3 HH, 3 HL.
    #   - Invalidation close at hour 7 (1.0760 < 1.0800 controlling HL).
    #   - Post-invalidation swings: 1 LH, 1 LL, then 1 more LH, 1 more LL.
    #     Episode-scoped, that's 2 LH + 2 LL and DOWNTREND could establish.
    #     BUT the first post-invalidation HIGH/LOW have no same-kind reference
    #     within the episode, so episode-scoped labels would be:
    #       hour 8: no prior HIGH in episode -> no label
    #       hour 9: no prior LOW in episode  -> no label
    #       hour 10: LH vs hour 8 (1.0850 < 1.0900)
    #       hour 11: LL vs hour 9 (1.0700 < 1.0750)
    #     That's 1 LH + 1 LL episode-scoped -- insufficient for DOWNTREND.
    #
    # Broken (count all historical labels):
    #   hour 8 vs hour 5 (1.0900 < 1.1000) -> LH
    #   hour 9 vs hour 6 (1.0750 < 1.0800) -> LL
    #   hour 10 vs hour 8 (1.0850 < 1.0900) -> LH
    #   hour 11 vs hour 9 (1.0700 < 1.0750) -> LL
    #   2 LH + 2 LL -> DOWNTREND establishes.
    engine = H1MarketStructureEngine()
    prior = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    post = [
        confirmed(8,  SwingKind.HIGH, "1.0900"),
        confirmed(9,  SwingKind.LOW,  "1.0750"),
        confirmed(10, SwingKind.HIGH, "1.0850"),
        confirmed(11, SwingKind.LOW,  "1.0700"),
    ]
    all_swings = prior + post
    labels = engine._relationship_labels(all_swings)
    invalidation = [candle(7, "1.0800", "1.0810", "1.0750", "1.0760")]
    regime, controlling, _, _ = engine._classify(invalidation, all_swings, labels, [])
    assert regime is not Regime.DOWNTREND, (
        f"post-invalidation episode has only 1 LH + 1 LL (hour 10 vs hour 8, "
        f"hour 11 vs hour 9); DOWNTREND requires 2 LH + 2 LL from post-swing "
        f"evidence only; prior-episode swings (hour 5 HH, hour 6 HL) must not "
        f"contribute; got {regime}"
    )


def test_t4_first_establishment_returns_uptrend_not_transition() -> None:
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    labels = engine._relationship_labels(swings)
    regime, _, _, _ = engine._classify([], swings, labels, [])
    assert regime is Regime.UPTREND, (
        f"first establishment of 2 HH + 2 HL with no prior invalidation must be "
        f"UPTREND, not TRANSITION; got {regime}"
    )

def test_t5_invalidation_requires_close_after_controlling_swing() -> None:
    # MS-0.1A §8: "UPTREND → completed H1 close below controlling HL."
    # MS-0.1A §10 / invariant 35: TRANSITION requires an invalidation within
    # the evaluated candles. A close below the controlling HL that occurred
    # BEFORE the controlling swing formed cannot invalidate it.
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),  # controlling HL at hour 6
    ]
    labels = engine._relationship_labels(swings)

    # Two candles passed to _classify:
    #   - hour 0: closes at 1.0700, BELOW the controlling HL 1.0800, but its
    #     timestamp_close (hour 1) is BEFORE the controlling swing's timestamp
    #     (hour 6). The timestamp guard must skip this candle.
    #   - hour 7: closes at 1.1050, ABOVE the controlling HL 1.0800, so it
    #     does not invalidate.
    candles = [
        candle(0, "1.0900", "1.0910", "1.0690", "1.0700"),
        candle(7, "1.1000", "1.1060", "1.0990", "1.1050"),
    ]
    regime, controlling, _, _ = engine._classify(candles, swings, labels, [])
    assert regime is Regime.UPTREND, (
        f"hour-0 close 1.0700 predates controlling HL 1.0800 (hour 6); "
        f"only closes after the controlling swing can invalidate; "
        f"got {regime}"
    )
    assert controlling == swings[5].swing

def test_t6_regime_persistence_across_evaluations() -> None:
    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    labels = engine._relationship_labels(swings)
    first, _, _, _ = engine._classify([], swings, labels, [])
    second, _, _, _ = engine._classify([], swings, labels, [])
    third, _, _, _ = engine._classify([], swings, labels, [])
    assert first == second == third, (
        f"identical inputs must produce identical regime; got {first}, {second}, {third}"
    )

def test_r13_opposing_swing_replacement_records_old_and_new_reference() -> None:
    # MS-0.1A §3: "When replacement occurs, rebind the pending confirmation
    # predicate to the new opposing reference. The active candidate's identity,
    # zone, and origin remain unchanged. Record the replacement and both the
    # old and new opposing references in structural_events."
    engine = H1MarketStructureEngine()
    candles = [
        candle(0, "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1, "1.1000", "1.1100", "1.1000", "1.1050"),  # HIGH candidate at hour 1
        candle(2, "1.1050", "1.1080", "1.1000", "1.1030"),
        candle(3, "1.1030", "1.1050", "1.0850", "1.0880"),  # LOW candidate at hour 3 (opposing)
        candle(4, "1.0880", "1.0950", "1.0870", "1.0930"),
        candle(5, "1.0930", "1.0950", "1.0800", "1.0850"),  # LOW at hour 5 (more extreme, replaces)
        candle(6, "1.0850", "1.0900", "1.0830", "1.0880"),
    ]
    events: list[str] = []
    candidates = engine._candidates(candles, [])
    engine._confirm_candidates(candles, candidates, events)

    updates = [e for e in events if e.startswith("OPPOSING_SWING_UPDATED:")]
    assert len(updates) == 1, f"expected exactly one OPPOSING_SWING_UPDATED, got {updates}"

    event = updates[0]
    old_ts = candles[3].timestamp_open.isoformat()
    new_ts = candles[5].timestamp_open.isoformat()
    assert old_ts in event, (
        f"R13 requires recording the old opposing reference {old_ts}; got {event}"
    )
    assert new_ts in event, (
        f"R13 requires recording the new opposing reference {new_ts}; got {event}"
    )

def test_r41_phase1_swing_classification_unresolved() -> None:
    # MS-0.1A section 6 + Amendment 05 section A: the first confirmed HIGH
    # and first confirmed LOW of an episode are admitted with
    # CLASSIFICATION_UNRESOLVED and emit SWING_CONFIRMED_UNRESOLVED:bootstrap.
    engine = H1MarketStructureEngine()
    candles = [
        candle(0,  "1.1000", "1.1050", "1.0950", "1.1000"),
        candle(1,  "1.1000", "1.1100", "1.1000", "1.1050"),
        candle(2,  "1.1050", "1.1080", "1.0980", "1.1000"),
        candle(3,  "1.1000", "1.1010", "1.0800", "1.0850"),
        candle(4,  "1.0850", "1.0880", "1.0820", "1.0830"),
        candle(5,  "1.0830", "1.0850", "1.0750", "1.0760"),
        candle(6,  "1.0760", "1.0800", "1.0750", "1.0770"),
        candle(7,  "1.0670", "1.0700", "1.0650", "1.0680"),
        candle(8,  "1.0680", "1.0750", "1.0680", "1.0700"),
        candle(9,  "1.0850", "1.0900", "1.0750", "1.0880"),
        candle(10, "1.0880", "1.0880", "1.0800", "1.0850"),
        candle(11, "1.0850", "1.0950", "1.0850", "1.0920"),
    ]
    state = engine.evaluate(
        candles=candles,
        evaluation_cutoff=candles[-1].timestamp_close,
    )
    ts_high = candles[1].timestamp_open
    ts_low = candles[7].timestamp_open

    phase1_high_events = [
        e for e in state.structural_events
        if e == f"SWING_MEANINGFUL_PHASE1:{ts_high.isoformat()}"
    ]
    phase1_low_events = [
        e for e in state.structural_events
        if e == f"SWING_MEANINGFUL_PHASE1:{ts_low.isoformat()}"
    ]
    bootstrap_high_events = [
        e for e in state.structural_events
        if e == f"SWING_CONFIRMED_UNRESOLVED:{ts_high.isoformat()}:bootstrap"
    ]
    bootstrap_low_events = [
        e for e in state.structural_events
        if e == f"SWING_CONFIRMED_UNRESOLVED:{ts_low.isoformat()}:bootstrap"
    ]
    assert len(phase1_high_events) == 1, (
        f"expected exactly one SWING_MEANINGFUL_PHASE1 for HIGH at hour 1; "
        f"got {phase1_high_events}"
    )
    assert len(phase1_low_events) == 1, (
        f"expected exactly one SWING_MEANINGFUL_PHASE1 for LOW at hour 7; "
        f"got {phase1_low_events}"
    )
    assert len(bootstrap_high_events) == 1, (
        f"expected exactly one SWING_CONFIRMED_UNRESOLVED:*:bootstrap for HIGH at hour 1; "
        f"got {bootstrap_high_events}"
    )
    assert len(bootstrap_low_events) == 1, (
        f"expected exactly one SWING_CONFIRMED_UNRESOLVED:*:bootstrap for LOW at hour 7; "
        f"got {bootstrap_low_events}"
    )

    records = state.classification_records
    assert len(records) == 2, (
        f"expected exactly 2 classification records (one per confirmed swing); "
        f"got {len(records)}"
    )
    for record in records:
        assert record.is_bootstrap is True, (
            f"all records should be bootstrap in this fixture; got {record}"
        )
        assert record.classification is None, (
            f"bootstrap records must have classification=None; got {record.classification}"
        )
    record_timestamps = {r.swing_timestamp for r in records}
    assert record_timestamps == {ts_high, ts_low}, (
        f"expected records for {ts_high} and {ts_low}; got {record_timestamps}"
    )


def test_r40_classification_and_reference_recorded() -> None:
    # MS-0.1A section 6, invariant 29: when a confirmed swing has a
    # same-kind reference, the engine records both the classification
    # (typed via SwingClassification) and the exact reference swing.
    from trading_system.domain import SwingClassification

    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
    ]
    result = engine._meaningful_swings(confirmed=swings)

    records_by_ts = {r.swing_timestamp: r for r in result.ledger.classification}

    ts_first_high = swings[0].swing.timestamp
    ts_first_low = swings[1].swing.timestamp
    ts_second_high = swings[2].swing.timestamp
    ts_second_low = swings[3].swing.timestamp

    assert ts_first_high in records_by_ts, "expected record for Phase 1 HIGH"
    assert records_by_ts[ts_first_high].is_bootstrap is True
    assert records_by_ts[ts_first_high].classification is None

    assert ts_first_low in records_by_ts, "expected record for Phase 1 LOW"
    assert records_by_ts[ts_first_low].is_bootstrap is True
    assert records_by_ts[ts_first_low].classification is None

    assert ts_second_high in records_by_ts, "expected record for second HIGH"
    assert records_by_ts[ts_second_high].is_bootstrap is False
    assert records_by_ts[ts_second_high].classification is SwingClassification.HH, (
        f"second HIGH should be HH vs first HIGH at 1.0800; "
        f"got {records_by_ts[ts_second_high].classification}"
    )
    assert records_by_ts[ts_second_high].reference_timestamp == ts_first_high

    assert ts_second_low in records_by_ts, "expected record for second LOW"
    assert records_by_ts[ts_second_low].is_bootstrap is False
    assert records_by_ts[ts_second_low].classification is SwingClassification.HL, (
        f"second LOW should be HL vs first LOW at 1.0600; "
        f"got {records_by_ts[ts_second_low].classification}"
    )
    assert records_by_ts[ts_second_low].reference_timestamp == ts_first_low


def test_r22_partial_classification_records_present() -> None:
    # MS-0.1A section 5 (partial): structural relationships determine current
    # active participation. This is a partial test for Round 1: it verifies
    # classification records exist for non-bootstrap swings, which is a
    # precondition for Round 2's admission gate. The full R22 invariant
    # (classification result determines admission) is verified in Round 2.
    from trading_system.domain import SwingClassification

    engine = H1MarketStructureEngine()
    swings = [
        confirmed(1, SwingKind.HIGH, "1.0800"),
        confirmed(2, SwingKind.LOW,  "1.0600"),
        confirmed(3, SwingKind.HIGH, "1.0900"),
        confirmed(4, SwingKind.LOW,  "1.0700"),
        confirmed(5, SwingKind.HIGH, "1.1000"),
        confirmed(6, SwingKind.LOW,  "1.0800"),
    ]
    result = engine._meaningful_swings(confirmed=swings)

    bootstrap_records = [r for r in result.ledger.classification if r.is_bootstrap]
    assert len(bootstrap_records) == 2, (
        f"expected exactly 2 bootstrap records; got {len(bootstrap_records)}"
    )
    for r in bootstrap_records:
        assert r.classification is None

    non_bootstrap = [r for r in result.ledger.classification if not r.is_bootstrap]
    assert len(non_bootstrap) == 4, (
        f"expected 4 non-bootstrap records; got {len(non_bootstrap)}"
    )
    for r in non_bootstrap:
        assert r.classification is not None, (
            f"non-bootstrap record must have classification; got None for {r.swing_timestamp}"
        )
        assert isinstance(r.classification, SwingClassification), (
            f"classification must be SwingClassification; got {type(r.classification)}"
        )