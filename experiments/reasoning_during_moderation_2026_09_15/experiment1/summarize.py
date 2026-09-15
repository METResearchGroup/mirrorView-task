"""Summarize experiment 1 thinking-token counts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --summarize
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    STATUS_EMPTY_THINKING,
    STATUS_TRUNCATED,
    STATUS_VALID,
)

GROUP_ORDER = (GROUP_SPLIT, GROUP_UNANIMOUS_KEEP, GROUP_UNANIMOUS_REMOVE)
PERCENTILE_P25 = 25
PERCENTILE_P75 = 75
EMPTY_RATE = 0.0


def summarize_tokens(traces: pd.DataFrame) -> pd.DataFrame:
    """Return one token-stat row per model and analysis group. No accuracy columns."""
    frame = pd.DataFrame(traces)
    model_ids = list(dict.fromkeys(frame["model_id"].tolist()))
    rows = [
        _group_row(frame, model_id, group)
        for model_id in model_ids
        for group in GROUP_ORDER
    ]
    return pd.DataFrame(rows)


def _group_row(frame: pd.DataFrame, model_id: str, group: str) -> dict[str, object]:
    """Build the identity and stats for one model-group cell."""
    subset = frame[(frame["model_id"] == model_id) & (frame["group"] == group)]
    return {"model_id": model_id, "group": group, **_token_stats(subset)}


def _token_stats(subset: pd.DataFrame) -> dict[str, float | int]:
    """Compute token columns for one model-group subset."""
    valid = subset[subset["status"] == STATUS_VALID]
    values = valid["thinking_token_count"].to_numpy(dtype=float)
    return {
        "n_posts": int(len(subset)),
        "n_valid": int(len(valid)),
        "mean": _stat_or_nan(values, np.mean),
        "median": _stat_or_nan(values, np.median),
        "p25": _percentile_or_nan(values, PERCENTILE_P25),
        "p75": _percentile_or_nan(values, PERCENTILE_P75),
        "max": _stat_or_nan(values, np.max),
        "truncated_rate": _status_rate(subset, STATUS_TRUNCATED),
        "empty_thinking_rate": _status_rate(subset, STATUS_EMPTY_THINKING),
    }


def _stat_or_nan(values: np.ndarray, fn: object) -> float:
    """Return `fn(values)` or NaN when the valid set is empty."""
    if len(values) == 0:
        return float("nan")
    return float(fn(values))


def _percentile_or_nan(values: np.ndarray, quantile: float) -> float:
    """Return the numpy percentile or NaN when the valid set is empty."""
    if len(values) == 0:
        return float("nan")
    return float(np.percentile(values, quantile))


def _status_rate(subset: pd.DataFrame, status: str) -> float:
    """Share of subset rows with `status`. Zero when the subset is empty."""
    if subset.empty:
        return EMPTY_RATE
    return float((subset["status"] == status).mean())
