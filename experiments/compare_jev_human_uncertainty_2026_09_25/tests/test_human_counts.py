"""Tests for five-labeler remove counts.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
"""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.compare_jev_human_uncertainty_2026_09_25.human_counts import (
    aggregate_remove_counts,
    build_five_labeler_counts,
    dedupe_labeler_post,
    posts_with_labeler_count,
    select_scored_trials,
)


def _trial(
    prolific_id: str,
    post_id: str,
    decision: str,
    trial_type: str = "moderation-trial",
    time_elapsed: int = 1,
    trial_index: int = 0,
) -> dict[str, object]:
    return {
        "prolific_id": prolific_id,
        "post_id": post_id,
        "decision": decision,
        "trial_type": trial_type,
        "time_elapsed": time_elapsed,
        "trial_index": trial_index,
    }


class TestSelectScoredTrials:
    """Tests for select_scored_trials."""

    def test_keeps_moderation_keep_and_remove(self) -> None:
        """Keeps keep and remove moderation trials and drops other rows."""
        raw = pd.DataFrame(
            [
                _trial("p1", "post-a", "keep"),
                _trial("p2", "post-a", "remove"),
                _trial("p3", "post-a", "keep", trial_type="instructions"),
                _trial("p4", "post-a", ""),
            ]
        )

        result = select_scored_trials(raw)

        assert list(result["prolific_id"]) == ["p1", "p2"]

    def test_drops_blank_post_id(self) -> None:
        """Drops a moderation keep row whose post id is blank."""
        raw = pd.DataFrame([_trial("p1", "", "keep"), _trial("p2", "post-a", "keep")])

        result = select_scored_trials(raw)

        assert list(result["post_id"]) == ["post-a"]

    def test_drops_missing_and_nan_post_id(self) -> None:
        """Drops a null post id and the text nan."""
        raw = pd.DataFrame(
            [
                _trial("p1", None, "keep"),
                _trial("p2", "NaN", "keep"),
                _trial("p3", "post-a", "keep"),
            ]
        )

        result = select_scored_trials(raw)

        assert list(result["post_id"]) == ["post-a"]

    def test_keeps_uppercase_keep_and_remove(self) -> None:
        """Keeps KEEP and REMOVE when the trial type is mixed case."""
        raw = pd.DataFrame(
            [
                _trial("p1", "post-a", "KEEP", trial_type="Moderation-Trial"),
                _trial("p2", "post-a", "REMOVE", trial_type="MODERATION-TRIAL"),
            ]
        )

        result = select_scored_trials(raw)

        assert list(result["decision"]) == ["keep", "remove"]

    def test_missing_column_raises(self) -> None:
        """Raises KeyError when decision is missing."""
        raw = pd.DataFrame([{"trial_type": "moderation-trial", "post_id": "post-a", "prolific_id": "p1"}])

        with pytest.raises(KeyError):
            select_scored_trials(raw)


class TestDedupeLabelerPost:
    """Tests for dedupe_labeler_post."""

    def test_keeps_first_row_per_person_and_post(self) -> None:
        """Keeps the earlier remove row when the same person rates the post twice."""
        trials = pd.DataFrame(
            [
                _trial("p1", "post-a", "keep", time_elapsed=20, trial_index=2),
                _trial("p1", "post-a", "remove", time_elapsed=10, trial_index=1),
            ]
        )

        result = dedupe_labeler_post(trials)

        assert len(result) == 1
        assert result.iloc[0]["decision"] == "remove"

    def test_keeps_lower_trial_index_when_elapsed_matches(self) -> None:
        """Keeps the lower trial index when elapsed time is the same."""
        trials = pd.DataFrame(
            [
                _trial("p1", "post-a", "keep", time_elapsed=10, trial_index=2),
                _trial("p1", "post-a", "remove", time_elapsed=10, trial_index=1),
            ]
        )

        result = dedupe_labeler_post(trials)

        assert result.iloc[0]["decision"] == "remove"


class TestAggregateRemoveCounts:
    """Tests for aggregate_remove_counts."""

    def test_counts_remove_votes(self) -> None:
        """Counts two remove votes among three trials on one post."""
        trials = pd.DataFrame(
            [
                _trial("p1", "post-a", "remove"),
                _trial("p2", "post-a", "remove"),
                _trial("p3", "post-a", "keep"),
            ]
        )
        expected_raters = 3
        expected_remove = 2

        result = aggregate_remove_counts(trials)

        assert result.iloc[0]["post_id"] == "post-a"
        assert int(result.iloc[0]["n_raters"]) == expected_raters
        assert int(result.iloc[0]["n_remove"]) == expected_remove


class TestPostsWithLabelerCount:
    """Tests for posts_with_labeler_count."""

    def test_keeps_exact_labeler_count(self) -> None:
        """Keeps the two posts that have five labelers."""
        counts = pd.DataFrame(
            [
                {"post_id": "post-a", "n_raters": 4, "n_remove": 1},
                {"post_id": "post-b", "n_raters": 5, "n_remove": 2},
                {"post_id": "post-c", "n_raters": 5, "n_remove": 0},
            ]
        )
        labeler_count = 5

        result = posts_with_labeler_count(counts, labeler_count)

        assert list(result["post_id"]) == ["post-b", "post-c"]

    def test_rejects_non_positive_labeler_count(self) -> None:
        """Raises ValueError when the labeler count is 0."""
        counts = pd.DataFrame([{"post_id": "post-a", "n_raters": 5, "n_remove": 1}])

        with pytest.raises(ValueError):
            posts_with_labeler_count(counts, 0)


class TestBuildFiveLabelerCounts:
    """Tests for build_five_labeler_counts."""

    def test_returns_only_posts_with_five_labelers(self) -> None:
        """Returns the five-labeler post and its remove count."""
        raw = pd.DataFrame(
            [
                _trial("p1", "post-a", "remove"),
                _trial("p2", "post-a", "remove"),
                _trial("p3", "post-a", "keep"),
                _trial("p4", "post-a", "keep"),
                _trial("p5", "post-a", "remove"),
                _trial("p1", "post-b", "keep"),
                _trial("p2", "post-b", "remove"),
            ]
        )
        expected_remove = 3

        result = build_five_labeler_counts(raw)

        assert list(result["post_id"]) == ["post-a"]
        assert int(result.iloc[0]["n_remove"]) == expected_remove
