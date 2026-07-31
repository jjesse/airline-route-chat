"""Simple sliding-window rate limiters for the Streamlit UI.

Two layers:
  1. Per-session (Streamlit session_state) — stops one browser tab from spamming
  2. Process-wide (module-level) — soft cap across all sessions on this worker

This is intentional defense-in-depth for a local/demo app, not a substitute
for authentication or a reverse-proxy rate limit on the public internet.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Optional, Tuple


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    retry_after_seconds: float = 0.0
    limit: int = 0
    window_seconds: float = 0.0

    @property
    def message(self) -> str:
        if self.allowed:
            return ""
        wait = max(1, int(self.retry_after_seconds + 0.999))
        return (
            f"Rate limit exceeded ({self.limit} per {int(self.window_seconds)}s). "
            f"Try again in about {wait}s."
        )


class SlidingWindowLimiter:
    """Allow at most `limit` events in the last `window_seconds`."""

    def __init__(self, limit: int, window_seconds: float) -> None:
        if limit < 1:
            raise ValueError("limit must be >= 1")
        if window_seconds <= 0:
            raise ValueError("window_seconds must be > 0")
        self.limit = int(limit)
        self.window_seconds = float(window_seconds)
        self._events: Deque[float] = deque()
        self._lock = threading.Lock()

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        while self._events and self._events[0] <= cutoff:
            self._events.popleft()

    def check(self, now: Optional[float] = None) -> RateLimitResult:
        """Non-mutating peek."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(now)
            if len(self._events) < self.limit:
                return RateLimitResult(
                    allowed=True,
                    limit=self.limit,
                    window_seconds=self.window_seconds,
                )
            retry = self.window_seconds - (now - self._events[0])
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=max(0.0, retry),
                limit=self.limit,
                window_seconds=self.window_seconds,
            )

    def allow(self, now: Optional[float] = None) -> RateLimitResult:
        """Record an event if under the limit; otherwise reject."""
        now = time.monotonic() if now is None else now
        with self._lock:
            self._prune(now)
            if len(self._events) < self.limit:
                self._events.append(now)
                return RateLimitResult(
                    allowed=True,
                    limit=self.limit,
                    window_seconds=self.window_seconds,
                )
            retry = self.window_seconds - (now - self._events[0])
            return RateLimitResult(
                allowed=False,
                retry_after_seconds=max(0.0, retry),
                limit=self.limit,
                window_seconds=self.window_seconds,
            )


# Defaults tuned for interactive local use (not hostile public traffic).
QUERY_SESSION_LIMIT = 30          # queries per window per browser session
QUERY_SESSION_WINDOW = 60.0       # seconds
QUERY_GLOBAL_LIMIT = 120          # across all sessions on this process
QUERY_GLOBAL_WINDOW = 60.0

UPLOAD_SESSION_LIMIT = 5
UPLOAD_SESSION_WINDOW = 300.0     # 5 minutes
UPLOAD_GLOBAL_LIMIT = 20
UPLOAD_GLOBAL_WINDOW = 300.0

_global_query = SlidingWindowLimiter(QUERY_GLOBAL_LIMIT, QUERY_GLOBAL_WINDOW)
_global_upload = SlidingWindowLimiter(UPLOAD_GLOBAL_LIMIT, UPLOAD_GLOBAL_WINDOW)

# session_id -> limiter (bounded growth)
_session_query: Dict[str, SlidingWindowLimiter] = {}
_session_upload: Dict[str, SlidingWindowLimiter] = {}
_session_lock = threading.Lock()
_MAX_SESSION_BUCKETS = 500


def _session_limiter(
    store: Dict[str, SlidingWindowLimiter],
    session_id: str,
    limit: int,
    window: float,
) -> SlidingWindowLimiter:
    with _session_lock:
        if session_id not in store:
            if len(store) >= _MAX_SESSION_BUCKETS:
                # Drop an arbitrary old entry to bound memory
                store.pop(next(iter(store)))
            store[session_id] = SlidingWindowLimiter(limit, window)
        return store[session_id]


def check_query_allowed(session_id: str) -> RateLimitResult:
    """Session + global limits for chat / route queries."""
    sid = (session_id or "anonymous")[:64]
    session = _session_limiter(
        _session_query, sid, QUERY_SESSION_LIMIT, QUERY_SESSION_WINDOW
    )
    s = session.allow()
    if not s.allowed:
        return s
    g = _global_query.allow()
    if not g.allowed:
        return g
    return s


def check_upload_allowed(session_id: str) -> RateLimitResult:
    """Session + global limits for CSV uploads."""
    sid = (session_id or "anonymous")[:64]
    session = _session_limiter(
        _session_upload, sid, UPLOAD_SESSION_LIMIT, UPLOAD_SESSION_WINDOW
    )
    s = session.allow()
    if not s.allowed:
        return s
    g = _global_upload.allow()
    if not g.allowed:
        return g
    return s


def reset_for_tests() -> None:
    """Clear process state (unit tests only)."""
    global _global_query, _global_upload
    with _session_lock:
        _session_query.clear()
        _session_upload.clear()
    _global_query = SlidingWindowLimiter(QUERY_GLOBAL_LIMIT, QUERY_GLOBAL_WINDOW)
    _global_upload = SlidingWindowLimiter(UPLOAD_GLOBAL_LIMIT, UPLOAD_GLOBAL_WINDOW)
