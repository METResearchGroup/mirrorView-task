"""Tests for mirrored_s3_key."""

from __future__ import annotations

import pytest

from experiments.ai_simulation_responses_2026_09_11.shared.write import mirrored_s3_key


class TestMirroredS3Key:
    """Tests for mirrored_s3_key function."""

    def test_cohort_users_key_equals_relative_path(self):
        """Cohort users parquet key matches the repo-relative path."""
        # Arrange
        relative_path = (
            "experiments/ai_simulation_responses_2026_09_11/shared/cohort_users.parquet"
        )

        # Act
        result = mirrored_s3_key(relative_path)

        # Assert
        expected = relative_path
        assert result == expected
        assert not result.startswith("experiments/experiments/")

    def test_experiment_five_csv_key_equals_relative_path(self):
        """Experiment 5 CSV key matches the repo-relative path."""
        # Arrange
        relative_path = (
            "experiments/ai_simulation_responses_2026_09_11/experiment5/"
            "outputs/false_negative_posts.csv"
        )

        # Act
        result = mirrored_s3_key(relative_path)

        # Assert
        assert result == relative_path

    def test_rejects_path_outside_experiment_prefix(self):
        """Paths outside the experiment prefix raise ValueError."""
        with pytest.raises(ValueError):
            mirrored_s3_key("shared/cohort_users.parquet")

    def test_rejects_leading_slash(self):
        """Leading slashes raise ValueError."""
        with pytest.raises(ValueError):
            mirrored_s3_key(
                "/experiments/ai_simulation_responses_2026_09_11/shared/"
                "cohort_users.parquet"
            )

    def test_rejects_older_finetune_prefix(self):
        """Older finetune prefix paths raise ValueError."""
        with pytest.raises(ValueError):
            mirrored_s3_key("mirrorview-finetune_qwen_model_2026_08_08/data/x.parquet")
