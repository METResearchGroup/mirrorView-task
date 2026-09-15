"""Summarize human response_time_ms on the three analysis groups.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment1.summarize import (
    GROUP_ORDER,
    PERCENTILE_P25,
    PERCENTILE_P75,
    _percentile_or_nan,
    _stat_or_nan,
)

RESPONSE_TIME_COLUMN = "response_time_ms"
ZERO_MS = 0.0
LEVEL_TRIAL = "trial"
LEVEL_POST_MEAN = "post_mean"


def usable_times(slim: pd.DataFrame) -> pd.DataFrame:
    """Keep finite response_time_ms values greater than zero. Do not read `rt`."""
    times = pd.to_numeric(slim[RESPONSE_TIME_COLUMN], errors="coerce")
    values = times.to_numpy(dtype=float)
    keep = np.isfinite(values) & (values > ZERO_MS)
    return slim.loc[keep].copy()


def trial_level_summary(slim: pd.DataFrame) -> pd.DataFrame:
    """Write n, mean, median, p25, p75, and max of usable trial times by group."""
    usable = usable_times(slim)
    return pd.DataFrame(
        [_level_row(usable, group, LEVEL_TRIAL) for group in GROUP_ORDER]
    )


def post_mean_summary(slim: pd.DataFrame) -> pd.DataFrame:
    """Average usable times per post, then write the same stats by group."""
    usable = usable_times(slim)
    post_means = usable.groupby(["post_id", "group"], as_index=False)[
        RESPONSE_TIME_COLUMN
    ].mean()
    return pd.DataFrame(
        [_level_row(post_means, group, LEVEL_POST_MEAN) for group in GROUP_ORDER]
    )


def _level_row(frame: pd.DataFrame, group: str, level: str) -> dict[str, object]:
    """Build one summary row for a group at trial or post-mean level."""
    subset = frame[frame["group"] == group]
    values = subset[RESPONSE_TIME_COLUMN].to_numpy(dtype=float)
    return {
        "level": level,
        "group": group,
        "n": int(len(subset)),
        "mean": _stat_or_nan(values, np.mean),
        "median": _stat_or_nan(values, np.median),
        "p25": _percentile_or_nan(values, PERCENTILE_P25),
        "p75": _percentile_or_nan(values, PERCENTILE_P75),
        "max": _stat_or_nan(values, np.max),
    }

