"""Summarize human response_time_ms on the three analysis groups.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment3/run.py
"""

from __future__ import annotations

import pandas as pd


def usable_times(slim: pd.DataFrame) -> pd.DataFrame:
    """Keep finite response_time_ms values greater than zero. Do not read `rt`."""
    raise NotImplementedError


def trial_level_summary(slim: pd.DataFrame) -> pd.DataFrame:
    """Write n, mean, median, p25, p75, and max of usable trial times by group."""
    raise NotImplementedError


def post_mean_summary(slim: pd.DataFrame) -> pd.DataFrame:
    """Average usable times per post, then write the same stats by group."""
    raise NotImplementedError
