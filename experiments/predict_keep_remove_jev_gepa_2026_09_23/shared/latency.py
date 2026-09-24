"""Latency timing helpers for Jev scoring.

Run from the repo root:

    PYTHONPATH=. uv run python -c "from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.latency import timed"
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import TypeVar

T = TypeVar("T")


def timed(func: Callable[..., T]) -> Callable[..., tuple[T, float]]:
    """Return (result, latency_ms). Re-raise exceptions unchanged."""

    def wrapper(*args: object, **kwargs: object) -> tuple[T, float]:
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
        except Exception:
            raise
        latency_ms = (time.perf_counter() - start) * 1000.0
        return result, latency_ms

    return wrapper


def percentile_ms(latencies: list[float], q: float) -> float:
    """Return q in [0,1] percentile with linear interpolation.

    Parameters
    ----------
    latencies
        Latency samples in milliseconds.
    q
        Quantile in ``[0, 1]``.

    Returns
    -------
    float
        Interpolated percentile, or ``0.0`` when ``latencies`` is empty.
    """
    if not latencies:
        return 0.0
    if q <= 0.0:
        return float(min(latencies))
    if q >= 1.0:
        return float(max(latencies))

    ordered = sorted(latencies)
    position = q * (len(ordered) - 1)
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    weight = position - lower_index
    lower_value = ordered[lower_index]
    upper_value = ordered[upper_index]
    return lower_value + (upper_value - lower_value) * weight
