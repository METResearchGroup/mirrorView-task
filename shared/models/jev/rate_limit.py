"""Request-start limiter for shared Jev scoring.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.models.jev.rate_limit import RequestStartLimiter; print(RequestStartLimiter.__name__)"
"""

from __future__ import annotations

from collections.abc import Callable


class RequestStartLimiter:
    """Allow at most a fixed number of request starts per minute."""

    def __init__(
        self,
        max_per_minute: int,
        clock: Callable[[], float],
        sleep_fn: Callable[[float], None],
    ) -> None:
        raise NotImplementedError

    def wait(self) -> None:
        """Block until another request is allowed to start."""
        raise NotImplementedError
