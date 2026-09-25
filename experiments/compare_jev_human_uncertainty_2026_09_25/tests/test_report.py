"""Tests for count tables and the results file.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_report.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    EXPECTED_FIVE_LABELER_POSTS,
    EXPECTED_JEV_BIN_COUNTS,
    EXPECTED_MEAN_DIFFERENCE,
    EXPECTED_REMOVE_COUNTS,
)
from experiments.compare_jev_human_uncertainty_2026_09_25.report import (
    assert_pinned_counts,
    write_count_tables,
    write_results,
)


def _expanded(counts: tuple[int, ...]) -> list[int]:
    values: list[int] = []
    for index, count in enumerate(counts):
        values.extend([index] * count)
    return values


def _pinned_shape(
    n_remove: list[int], jev_bin: list[int], difference: float
) -> pd.DataFrame:
    row_count = len(n_remove)
    return pd.DataFrame(
        {
            "post_id": [f"p{index}" for index in range(row_count)],
            "n_remove": n_remove,
            "p_remove": [0.1] * row_count,
            "jev_bin": jev_bin,
            "difference_score": [difference] * row_count,
        }
    )


def _comparison_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["a", "b"],
            "n_remove": [0, 1],
            "p_remove": [0.1, 0.85],
            "jev_bin": [0, 4],
            "difference_score": [0, -3],
        }
    )


class TestAssertPinnedCounts:
    """Tests for assert_pinned_counts."""

    def test_rejects_short_frame(self) -> None:
        """Raises ValueError when the frame is one row."""
        frame = _comparison_frame().iloc[:1].copy()

        with pytest.raises(ValueError):
            assert_pinned_counts(frame)

    def test_rejects_wrong_remove_counts(self) -> None:
        """Raises ValueError when the row count and bins match and remove counts do not."""
        zeros = [0] * EXPECTED_FIVE_LABELER_POSTS
        frame = _pinned_shape(
            zeros, _expanded(EXPECTED_JEV_BIN_COUNTS), EXPECTED_MEAN_DIFFERENCE
        )

        with pytest.raises(ValueError, match="remove counts"):
            assert_pinned_counts(frame)

    def test_rejects_wrong_bin_counts(self) -> None:
        """Raises ValueError when the row count and remove counts match and bins do not."""
        zeros = [0] * EXPECTED_FIVE_LABELER_POSTS
        frame = _pinned_shape(
            _expanded(EXPECTED_REMOVE_COUNTS), zeros, EXPECTED_MEAN_DIFFERENCE
        )

        with pytest.raises(ValueError, match="Jev bin counts"):
            assert_pinned_counts(frame)

    def test_rejects_wrong_mean(self) -> None:
        """Raises ValueError when the histograms match and the mean does not."""
        frame = _pinned_shape(
            _expanded(EXPECTED_REMOVE_COUNTS), _expanded(EXPECTED_JEV_BIN_COUNTS), 0.0
        )

        with pytest.raises(ValueError, match="mean difference"):
            assert_pinned_counts(frame)


class TestWriteCountTables:
    """Tests for write_count_tables."""

    def test_writes_remove_counts(self, tmp_path: Path) -> None:
        """Writes one post for remove counts 0 and 1."""
        paths = write_count_tables(_comparison_frame(), tmp_path)
        table = pd.read_csv(paths[0])
        expected = 1

        zero = table.loc[table["n_remove"].eq(0), "n_posts"]
        one = table.loc[table["n_remove"].eq(1), "n_posts"]
        assert int(zero.iloc[0]) == expected
        assert int(one.iloc[0]) == expected

    def test_writes_zero_for_absent_remove_counts(self, tmp_path: Path) -> None:
        """Writes zero posts for remove counts that are absent from the frame."""
        paths = write_count_tables(_comparison_frame(), tmp_path)
        table = pd.read_csv(paths[0])
        expected = 0

        five = table.loc[table["n_remove"].eq(5), "n_posts"]
        assert int(five.iloc[0]) == expected


class TestWriteResults:
    """Tests for write_results."""

    def test_links_figures_and_states_no_skip(self, tmp_path: Path) -> None:
        """Links the human figure and states that moderation trials have no skip."""
        path = write_results(_comparison_frame(), tmp_path / "RESULTS.md")
        text = path.read_text(encoding="utf-8")

        assert "human_remove_counts.png" in text
        assert "jev_six_bins.png" in text
        assert "Moderation trials have no skip decision." in text
        assert "6 equal bins" in text
