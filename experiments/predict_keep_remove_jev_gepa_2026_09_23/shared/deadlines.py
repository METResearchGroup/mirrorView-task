"""Interrupt a blocked socket call with SIGALRM.

``Thread.join(timeout)`` did not return while a worker blocked in SSL read.
"""

from __future__ import annotations

import signal
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def run_with_alarm(seconds: float, fn: Callable[[], T], *, label: str) -> T:
    """Run ``fn`` and raise ``TimeoutError`` if it is still blocked after ``seconds``."""

    def _on_alarm(signum: int, frame: object) -> None:
        raise TimeoutError(f"{label} exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        return fn()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
