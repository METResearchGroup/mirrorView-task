"""Retry helper with auth fail-fast for Jev API calls.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_retries.py -q
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

from typesafe_sdk import TypeSafeAuthenticationError, TypeSafePermissionDeniedError

MAX_EXTRA_ATTEMPTS = 3
BACKOFF_SECONDS = (1.0, 2.0, 4.0)

AUTH_ERROR_TYPES = (TypeSafeAuthenticationError, TypeSafePermissionDeniedError)

T = TypeVar("T")


def run_with_retries(
    fn: Callable[[], T],
    *,
    max_extra_attempts: int = MAX_EXTRA_ATTEMPTS,
    backoff_seconds: tuple[float, ...] = BACKOFF_SECONDS,
) -> T:
    """Call fn up to 1 + max_extra_attempts times.

    Auth errors propagate immediately. Other exceptions sleep 1/2/4 s between tries.

    Parameters
    ----------
    fn
        Callable to execute.
    max_extra_attempts
        Additional attempts after the first failure.
    backoff_seconds
        Sleep durations between retries.

    Returns
    -------
    T
        Return value from ``fn``.

    Raises
    ------
    Exception
        The last exception when all attempts are exhausted.
    """
    total_attempts = 1 + max_extra_attempts
    last_error: Exception | None = None
    for attempt_index in range(total_attempts):
        try:
            return fn()
        except AUTH_ERROR_TYPES:
            raise
        except Exception as exc:
            last_error = exc
            if attempt_index >= total_attempts - 1:
                break
            sleep_index = min(attempt_index, len(backoff_seconds) - 1)
            time.sleep(backoff_seconds[sleep_index])
    assert last_error is not None
    raise last_error
