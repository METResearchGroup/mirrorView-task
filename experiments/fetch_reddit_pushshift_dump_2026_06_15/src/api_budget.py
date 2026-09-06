"""Track a single scoring session's Perspective API budget."""

from __future__ import annotations

from experiments.fetch_reddit_pushshift_dump_2026_06_15.src.config import MAX_SESSION_API_CALLS

_used: int = 0


def reset_session_budget() -> None:
    """Reset the in-memory call counter for a new orchestration session."""

    global _used
    _used = 0


def api_calls_used() -> int:
    """Return how many Perspective calls have been spent this session."""

    return _used


def api_calls_remaining() -> int:
    """Return the remaining calls available before the session cap is hit."""

    return max(0, MAX_SESSION_API_CALLS - _used)


def budget_exhausted() -> bool:
    """Report whether the session has consumed its entire API budget."""

    return _used >= MAX_SESSION_API_CALLS


def record_api_calls(n: int) -> None:
    """Accumulate completed Perspective calls against the session cap.

    Parameters
    ----------
    n : int
        Number of API calls that were attempted in the most recent batch.
        Non-positive values are ignored.
    """

    global _used
    if n <= 0:
        return
    _used = min(MAX_SESSION_API_CALLS, _used + n)


def grant_api_calls(requested: int) -> int:
    """Return how many calls can be spent without exceeding the session cap.

    Parameters
    ----------
    requested : int
        Number of calls the caller would like to spend.

    Returns
    -------
    int
        The permitted call count after accounting for the remaining budget.
    """

    if requested <= 0:
        return 0
    return min(requested, api_calls_remaining())

