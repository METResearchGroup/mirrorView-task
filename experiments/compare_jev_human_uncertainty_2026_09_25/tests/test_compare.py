"""Tests for the human and Jev join.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_compare.py -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.compare_jev_human_uncertainty_2026_09_25.compare import (
    build_comparison_frame,
    join_on_post_id,
)


class TestJoinOnPostId:
    """Tests for join_on_post_id."""

    def test_inner_join_drops_unmatched_posts(self) -> None:
        """Keeps only the post that is in both frames."""
        human = pd.DataFrame(
            {"post_id": ["a", "b"], "n_remove": [1, 2], "n_raters": [5, 5]}
        )
        jev = pd.DataFrame({"post_id": ["b", "c"], "p_remove": [0.3, 0.9]})

        result = join_on_post_id(human, jev)

        assert list(result["post_id"]) == ["b"]
        assert list(result.columns) == ["post_id", "n_remove", "p_remove"]

    def test_duplicate_post_id_raises(self) -> None:
        """Raises ValueError when the human frame repeats a post id."""
        human = pd.DataFrame(
            {"post_id": ["a", "a"], "n_remove": [1, 2], "n_raters": [5, 5]}
        )
        jev = pd.DataFrame({"post_id": ["a"], "p_remove": [0.3]})

        with pytest.raises(ValueError):
            join_on_post_id(human, jev)

    def test_duplicate_jev_post_id_raises(self) -> None:
        """Raises ValueError when the Jev frame repeats a post id."""
        human = pd.DataFrame({"post_id": ["a"], "n_remove": [1], "n_raters": [5]})
        jev = pd.DataFrame({"post_id": ["a", "a"], "p_remove": [0.3, 0.4]})

        with pytest.raises(ValueError):
            join_on_post_id(human, jev)


class TestBuildComparisonFrame:
    """Tests for build_comparison_frame."""

    def test_difference_score_matches_issue_example(self) -> None:
        """One remove vote and a probability in bin 0 has difference 1."""
        human = pd.DataFrame({"post_id": ["a"], "n_remove": [1], "n_raters": [5]})
        jev = pd.DataFrame({"post_id": ["a"], "p_remove": [0.1]})

        result = build_comparison_frame(human, jev)

        assert int(result.iloc[0]["jev_bin"]) == 0
        assert int(result.iloc[0]["difference_score"]) == 1

    def test_does_not_mutate_inputs(self) -> None:
        """Leaves the input frames without a jev_bin column."""
        human = pd.DataFrame({"post_id": ["a"], "n_remove": [1], "n_raters": [5]})
        jev = pd.DataFrame({"post_id": ["a"], "p_remove": [0.1]})

        build_comparison_frame(human, jev)

        assert "jev_bin" not in human.columns
        assert "jev_bin" not in jev.columns
