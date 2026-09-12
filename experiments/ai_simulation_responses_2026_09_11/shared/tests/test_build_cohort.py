"""Tests for build_cohort."""

from __future__ import annotations

import json

import pandas as pd
import pytest

from experiments.ai_simulation_responses_2026_09_11.shared.cohort import build_cohort
from experiments.ai_simulation_responses_2026_09_11.shared.constants import POSTS_PER_USER


class TestBuildCohort:
    """Tests for build_cohort function."""

    def test_sorts_complete_users_by_epoch_then_prolific_id(
        self, make_cohort_csv, tmp_path
    ):
        """Three complete users with epochs 30, 10, and 20 sort earliest first."""
        # Arrange
        paths = make_cohort_csv(
            [("user-c", 30), ("user-a", 10), ("user-b", 20)],
        )
        expected = ("user-a", "user-b", "user-c")

        # Act
        result = build_cohort(paths)

        # Assert
        prolific_ids = tuple(user.prolific_id for user in result.users)
        assert prolific_ids == expected
        assert all(len(result.trials) == POSTS_PER_USER * len(result.users) for _ in [0])
        for user in result.users:
            user_trials = [t for t in result.trials if t.prolific_id == user.prolific_id]
            assert [t.pair_index for t in user_trials] == list(
                range(1, POSTS_PER_USER + 1)
            )

    def test_drops_user_with_nineteen_linked_fate_decisions(
        self, make_cohort_csv, tmp_path
    ):
        """A user with 19 linked-fate decisions is dropped as incomplete."""
        # Arrange
        rows = []
        for trial_index in range(19):
            rows.append(
                {
                    "prolific_id": "incomplete-user",
                    "participant_id": "pid-incomplete",
                    "trial_index": trial_index,
                    "evaluation_mode": "linked_fate",
                    "decision": "keep",
                    "phase": 1,
                    "pair_order": json.dumps(["original", "mirror"]),
                    "original_text": "orig",
                    "mirror_text": "mir",
                    "post_id": f"post-{trial_index}",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "sample_low_toxicity",
                    "phase1_pair_reflection_text": "text",
                    "phase1_pair_influence_rating": 4,
                }
            )
        path = tmp_path / "data_10_incomplete-user.csv"
        pd.DataFrame(rows).to_csv(path, index=False)

        # Act
        result = build_cohort([path])

        # Assert
        assert result.users == ()
        assert result.dropped_incomplete == 1

    def test_drops_user_with_missing_pair_order(self, make_cohort_csv, tmp_path):
        """A user with missing pair_order is dropped."""
        # Arrange
        rows = []
        for trial_index in range(POSTS_PER_USER):
            row = {
                "prolific_id": "bad-order",
                "participant_id": "pid-bad",
                "trial_index": trial_index,
                "evaluation_mode": "linked_fate",
                "decision": "keep",
                "phase": 1,
                "original_text": "orig",
                "mirror_text": "mir",
                "post_id": f"post-{trial_index}",
                "sampled_stance": "left",
                "sample_toxicity_type": "sample_low_toxicity",
                "phase1_pair_reflection_text": "text",
                "phase1_pair_influence_rating": 4,
            }
            if trial_index == 5:
                row["pair_order"] = ""
            else:
                row["pair_order"] = json.dumps(["original", "mirror"])
            rows.append(row)
        path = tmp_path / "data_10_bad-order.csv"
        pd.DataFrame(rows).to_csv(path, index=False)

        # Act
        result = build_cohort([path])

        # Assert
        assert result.users == ()
        assert result.dropped_missing_pair_order == 1

    def test_drops_user_with_empty_reflection(self, make_cohort_csv):
        """A user with empty reflection text is dropped."""
        # Arrange
        paths = make_cohort_csv([("no-reflection", 10)], reflection_text="")

        # Act
        result = build_cohort(paths)

        # Assert
        assert result.users == ()
        assert result.dropped_missing_reflection == 1

    def test_caps_at_one_thousand_complete_users(self, make_cohort_csv):
        """One thousand complete users are kept and the latest epoch is excluded."""
        # Arrange
        users = [(f"user-{index:04d}", index) for index in range(1001)]
        paths = make_cohort_csv(users)

        # Act
        result = build_cohort(paths)

        # Assert
        assert len(result.users) == 1000
        prolific_ids = {user.prolific_id for user in result.users}
        assert "user-1000" not in prolific_ids
        assert result.users[-1].source_file_epoch_ms == 999
