"""Request-start rate limiter for Jev API calls.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/shared/tests/test_rate_limiter.py -q
"""

from __future__ import annotations

import threading
import time

WINDOW_SECONDS = 60.0


class RequestStartLimiter:
    """Sliding-window limiter for API request starts."""

    def __init__(self, max_starts_per_minute: int) -> None:
        if max_starts_per_minute <= 0:
            raise ValueError("max_starts_per_minute must be positive")
        self._max_starts_per_minute = max_starts_per_minute
        self._lock = threading.Lock()
        self._start_times: list[float] = []

    def wait(self) -> None:
        """Block until another request start is allowed within the window."""
        while True:
            with self._lock:
                now = time.monotonic()
                cutoff = now - WINDOW_SECONDS
                self._start_times = [ts for ts in self._start_times if ts > cutoff]
                if len(self._start_times) < self._max_starts_per_minute:
                    self._start_times.append(now)
                    return
                oldest = self._start_times[0]
                sleep_seconds = oldest + WINDOW_SECONDS - now
            if sleep_seconds > 0:
                time.sleep(sleep_seconds)
