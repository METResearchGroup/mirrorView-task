"""Interrupt a blocked socket call with SIGALRM.

``Thread.join(timeout)`` did not return while a worker blocked in SSL read.
"""

from __future__ import annotations

import signal
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


class _AlarmInterrupt(BaseException):
    """BaseException so HTTP libraries that catch Exception cannot swallow the deadline."""


def run_with_alarm(seconds: float, fn: Callable[[], T], *, label: str) -> T:
    """Run ``fn`` and raise ``TimeoutError`` if it is still blocked after ``seconds``."""

    def _on_alarm(signum: int, frame: object) -> None:
        raise _AlarmInterrupt(f"{label} exceeded {seconds}s")

    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        try:
            return fn()
        except _AlarmInterrupt as exc:
            raise TimeoutError(str(exc)) from exc
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)
