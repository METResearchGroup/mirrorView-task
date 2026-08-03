"""Session-scoped Perspective API call budget."""

from __future__ import annotations

from experiments.fetch_reddit_pushshift_dump_2026_06_15.config import MAX_SESSION_API_CALLS

_used: int = 0


def reset_session_budget() -> None:
    global _used
    _used = 0


def api_calls_used() -> int:
    return _used


def api_calls_remaining() -> int:
    return max(0, MAX_SESSION_API_CALLS - _used)


def budget_exhausted() -> bool:
    return _used >= MAX_SESSION_API_CALLS


def record_api_calls(n: int) -> None:
    """Record n Perspective analyze() calls against the session budget."""

    global _used
    if n <= 0:
        return
    _used = min(MAX_SESSION_API_CALLS, _used + n)


def grant_api_calls(requested: int) -> int:
    """Return how many calls may be made without exceeding the session budget."""

    if requested <= 0:
        return 0
    return min(requested, api_calls_remaining())

