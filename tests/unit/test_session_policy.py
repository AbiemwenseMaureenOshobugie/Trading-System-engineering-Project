"""Acceptance tests for the deterministic MS-0.8 Session Policy Engine."""

from datetime import datetime, timezone

import pytest

from trading_system.session import SessionIdentity, SessionPolicyEngine


ENGINE = SessionPolicyEngine()


def utc(day: int, hour: int, minute: int = 0) -> datetime:
    return datetime(2026, 1, day, hour, minute, tzinfo=timezone.utc)


def test_ms08_t01_london_session_identity() -> None:
    result = ENGINE.evaluate(utc(5, 9))
    assert result.session_identity is SessionIdentity.LONDON


def test_ms08_t02_overlap_identity() -> None:
    result = ENGINE.evaluate(utc(5, 12))
    assert result.session_identity is SessionIdentity.LONDON_NEW_YORK_OVERLAP


def test_ms08_t03_asian_identity() -> None:
    result = ENGINE.evaluate(utc(5, 3))
    assert result.session_identity is SessionIdentity.ASIAN


def test_ms08_t04_new_york_identity() -> None:
    result = ENGINE.evaluate(utc(5, 18))
    assert result.session_identity is SessionIdentity.NEW_YORK


def test_ms08_t05_outside_identity() -> None:
    result = ENGINE.evaluate(utc(5, 22))
    assert result.session_identity is SessionIdentity.OUTSIDE_SESSION


def test_ms08_t06_london_permitted_monday_to_friday() -> None:
    for day in range(5, 10):
        result = ENGINE.evaluate(utc(day, 9))
        assert result.is_trading_permitted is True


def test_ms08_t07_overlap_permitted_monday_to_friday() -> None:
    for day in range(5, 10):
        result = ENGINE.evaluate(utc(day, 12))
        assert result.is_trading_permitted is True


def test_ms08_t08_asian_not_permitted() -> None:
    result = ENGINE.evaluate(utc(5, 3))
    assert result.is_trading_permitted is False


def test_ms08_t09_new_york_not_permitted() -> None:
    result = ENGINE.evaluate(utc(5, 18))
    assert result.is_trading_permitted is False


def test_ms08_t10_saturday_not_permitted() -> None:
    result = ENGINE.evaluate(utc(10, 9))
    assert result.timestamp_utc.weekday() == 5
    assert result.is_trading_permitted is False


def test_ms08_t11_sunday_not_permitted() -> None:
    result = ENGINE.evaluate(utc(11, 9))
    assert result.timestamp_utc.weekday() == 6
    assert result.is_trading_permitted is False


def test_ms08_t12_no_holiday_logic_is_applied() -> None:
    result = ENGINE.evaluate(datetime(2026, 12, 25, 9, tzinfo=timezone.utc))
    assert result.session_identity is SessionIdentity.LONDON
    assert result.is_trading_permitted is True


def test_ms08_t13_no_dst_adjustment_is_applied() -> None:
    assert ENGINE.evaluate(utc(5, 7)).session_identity is SessionIdentity.LONDON
    assert ENGINE.evaluate(utc(5, 16)).session_identity is SessionIdentity.NEW_YORK


def test_ms08_t14_result_is_deterministic() -> None:
    timestamp = utc(5, 12, 30)
    first = ENGINE.evaluate(timestamp)
    second = ENGINE.evaluate(timestamp)
    assert first == second


def test_ms08_t15_eligibility_is_authoritative_not_reason() -> None:
    permitted = ENGINE.evaluate(utc(5, 9))
    blocked = ENGINE.evaluate(utc(5, 18))

    assert permitted.is_trading_permitted is True
    assert permitted.reason is None
    assert blocked.is_trading_permitted is False
    assert blocked.reason is not None
    assert blocked.reason != "is_trading_permitted"


def test_session_result_derived_properties() -> None:
    london = ENGINE.evaluate(utc(5, 9))
    overlap = ENGINE.evaluate(utc(5, 12))
    asian = ENGINE.evaluate(utc(5, 3))

    assert london.is_london_session is True
    assert london.is_overlap is False
    assert london.is_asian_session is False
    assert overlap.is_london_session is False
    assert overlap.is_overlap is True
    assert asian.is_asian_session is True


def test_rejects_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        ENGINE.evaluate(datetime(2026, 1, 5, 9))
