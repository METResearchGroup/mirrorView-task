"""Tests for Jev label checks and probability bins.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.compare_jev_human_uncertainty_2026_09_25.compare import (
    jev_bin_for_probability,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    EXPECTED_JEV_ROWS,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.jev_labels import (
    assert_jev_label_frame,
)


def _labels(row_count: int, probability: float | None = 0.5) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": [f"p{index}" for index in range(row_count)],
            "p_remove": [probability] * row_count,
        }
    )


class TestAssertJevLabelFrame:
    """Tests for assert_jev_label_frame."""

    def test_accepts_complete_frame(self) -> None:
        """Accepts 19,219 rows with unique post ids and a probability."""
        labels = _labels(EXPECTED_JEV_ROWS)

        assert_jev_label_frame(labels)

    def test_rejects_missing_probability(self) -> None:
        """Raises ValueError when one probability is missing."""
        labels = _labels(EXPECTED_JEV_ROWS)
        labels.loc[0, "p_remove"] = None

        with pytest.raises(ValueError):
            assert_jev_label_frame(labels)

    def test_rejects_wrong_row_count(self) -> None:
        """Raises ValueError when the frame is not 19,219 rows."""
        labels = _labels(3)

        with pytest.raises(ValueError):
            assert_jev_label_frame(labels)


class TestJevBinForProbability:
    """Tests for jev_bin_for_probability."""

    @pytest.mark.parametrize(
        ("probability", "expected"),
        [
            (0.0, 0),
            (0.199, 0),
            (0.2, 1),
            (0.4, 2),
            (0.6, 3),
            (0.8, 4),
            (0.95, 4),
            (1.0, 4),
        ],
    )
    def test_bin_edges(self, probability: float, expected: int) -> None:
        """Maps probability edges onto bins 0 through 4.

        Parameters
        ----------
        probability
            Jev remove probability.
        expected
            Bin index for that probability.
        """
        result = jev_bin_for_probability(probability)

        assert result == expected

    def test_rejects_above_one(self) -> None:
        """Raises ValueError when the probability is above 1."""
        with pytest.raises(ValueError):
            jev_bin_for_probability(1.01)

    def test_rejects_below_zero(self) -> None:
        """Raises ValueError when the probability is below 0."""
        with pytest.raises(ValueError):
            jev_bin_for_probability(-0.01)
