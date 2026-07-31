"""Tests for sliding-window rate limiting."""

from __future__ import annotations

from rate_limit import (
    SlidingWindowLimiter,
    check_query_allowed,
    check_upload_allowed,
    reset_for_tests,
    QUERY_SESSION_LIMIT,
)


def setup_function():
    reset_for_tests()


def test_allows_under_limit():
    lim = SlidingWindowLimiter(3, 60.0)
    assert lim.allow(now=0.0).allowed
    assert lim.allow(now=1.0).allowed
    assert lim.allow(now=2.0).allowed


def test_blocks_over_limit():
    lim = SlidingWindowLimiter(2, 10.0)
    assert lim.allow(now=0.0).allowed
    assert lim.allow(now=1.0).allowed
    blocked = lim.allow(now=2.0)
    assert not blocked.allowed
    assert blocked.retry_after_seconds > 0


def test_window_rolls():
    lim = SlidingWindowLimiter(2, 10.0)
    assert lim.allow(now=0.0).allowed
    assert lim.allow(now=1.0).allowed
    assert not lim.allow(now=2.0).allowed
    # After window passes, earliest event expires
    assert lim.allow(now=10.1).allowed


def test_query_session_limit():
    reset_for_tests()
    sid = "test-session-a"
    for _ in range(QUERY_SESSION_LIMIT):
        assert check_query_allowed(sid).allowed
    blocked = check_query_allowed(sid)
    assert not blocked.allowed
    assert "Rate limit" in blocked.message


def test_different_sessions_independent():
    reset_for_tests()
    for _ in range(QUERY_SESSION_LIMIT):
        assert check_query_allowed("s1").allowed
    assert not check_query_allowed("s1").allowed
    assert check_query_allowed("s2").allowed


def test_upload_limit_stricter():
    reset_for_tests()
    sid = "up-1"
    # Default upload session limit is 5 / 5 min
    for _ in range(5):
        assert check_upload_allowed(sid).allowed
    assert not check_upload_allowed(sid).allowed
