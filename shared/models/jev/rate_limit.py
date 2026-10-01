"""Request-start limiter for shared Jev scoring.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.rate_limit import RequestStartLimiter; print(RequestStartLimiter.__name__)"
"""

from __future__ import annotations

import threading
from collections.abc import Callable


class RequestStartLimiter:
    """Allow at most a fixed number of request starts per minute."""

    def __init__(
        self,
        max_per_minute: int,
        clock: Callable[[], float],
        sleep_fn: Callable[[float], None],
    ) -> None:
        if max_per_minute <= 0:
            raise ValueError("max_per_minute must be positive")
        self._max_per_minute = max_per_minute
        self._clock = clock
        self._sleep_fn = sleep_fn
        self._lock = threading.Lock()
        self._start_times: list[float] = []

    def wait(self) -> None:
        """Block until another request is allowed to start."""
        while True:
            with self._lock:
                now = self._clock()
                cutoff = now - 60.0
                self._start_times = [stamp for stamp in self._start_times if stamp > cutoff]
                if len(self._start_times) < self._max_per_minute:
                    self._start_times.append(now)
                    return
                sleep_seconds = self._start_times[0] + 60.0 - now
            if sleep_seconds > 0:
                self._sleep_fn(sleep_seconds)
