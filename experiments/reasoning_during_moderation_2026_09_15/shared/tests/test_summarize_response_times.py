"""Tests for usable_times(), trial_level_summary(), and post_mean_summary()."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.reasoning_during_moderation_2026_09_15.experiment3.summarize import (
    post_mean_summary,
    trial_level_summary,
    usable_times,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GROUP_SPLIT,
)

RT_SENTINEL = 999
TIME_A1 = 10
TIME_A2 = 30
TIME_B = 20
TIME_KEEP_LOW = 1000
TIME_KEEP_HIGH = 2000
EXPECTED_TRIAL_N = 3
EXPECTED_TRIAL_MEDIAN = 20
EXPECTED_POST_N = 2
EXPECTED_POST_MEAN = 20.0


def _usable_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["a", "b", "c", "d", "e"],
            "group": [GROUP_SPLIT] * 5,
            "response_time_ms": [TIME_KEEP_LOW, TIME_KEEP_HIGH, np.nan, 0, -5],
            "rt": [RT_SENTINEL] * 5,
        }
    )


def _summary_input() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["A", "A", "B"],
            "group": [GROUP_SPLIT, GROUP_SPLIT, GROUP_SPLIT],
            "response_time_ms": [TIME_A1, TIME_A2, TIME_B],
            "rt": [RT_SENTINEL, RT_SENTINEL, RT_SENTINEL],
        }
    )


class TestUsableTimes:
    """Tests for usable_times function."""

    def test_keeps_positive_finite_times_and_ignores_rt(self) -> None:
        """Verifies NA, zero, and negative times drop while rt is unused."""
        slim = _usable_input()
        expected = [TIME_KEEP_LOW, TIME_KEEP_HIGH]

        result = usable_times(slim)

        assert result["response_time_ms"].tolist() == expected
        assert RT_SENTINEL not in result["response_time_ms"].tolist()


class TestTrialLevelSummary:
    """Tests for trial_level_summary function."""

    def test_split_n_and_median(self) -> None:
        """Verifies trial-level n and median on three split times."""
        slim = _summary_input()

        result = trial_level_summary(slim)
        row = result[result["group"] == GROUP_SPLIT].iloc[0]

        assert int(row["n"]) == EXPECTED_TRIAL_N
        assert float(row["median"]) == EXPECTED_TRIAL_MEDIAN


class TestPostMeanSummary:
    """Tests for post_mean_summary function."""

    def test_two_posts_with_equal_means(self) -> None:
        """Verifies post-mean n is 2 and both post means are 20."""
        slim = _summary_input()

        result = post_mean_summary(slim)
        row = result[result["group"] == GROUP_SPLIT].iloc[0]

        assert int(row["n"]) == EXPECTED_POST_N
        assert float(row["mean"]) == EXPECTED_POST_MEAN
        assert float(row["median"]) == EXPECTED_POST_MEAN
