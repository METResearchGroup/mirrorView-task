"""Tests for full-cohort --model labeling paths and approval gate."""

from __future__ import annotations

import io
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from data_platform.generate_features.s3_feature_campaign import StoredObject
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    COHORT_USERS_KEY,
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_OPENAI,
    OUTPUT_S3_BUCKET,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import render_user_prompt
from experiments.ai_simulation_responses_2026_09_11.shared.run import (
    APPROVAL_PATH,
    COST_ESTIMATE_RELATIVE_PATH,
    EXPERIMENT2_SETUP_PATH,
    full_feature_paths,
    load_cohort_users,
    require_model_approval,
)


class TestFullFeaturePaths:
    """Tests for full_feature_paths function."""

    @pytest.mark.parametrize(
        ("experiment_number", "model_folder"),
        [
            (1, MODEL_FOLDER_OPENAI),
            (2, MODEL_FOLDER_BEDROCK_CLAUDE),
            (3, MODEL_FOLDER_OPENAI),
            (4, MODEL_FOLDER_BEDROCK_CLAUDE),
        ],
    )
    def test_prefix_is_experiment_outputs_model_without_smoke(
        self, experiment_number: int, model_folder: str
    ):
        """Full-cohort paths use experiment{N}/outputs/{model}/ and never smoke/."""
        # Arrange
        expected_segment = f"experiment{experiment_number}/outputs/{model_folder}/"

        # Act
        result = full_feature_paths(experiment_number, model_folder)

        # Assert
        assert result.bucket == OUTPUT_S3_BUCKET
        assert expected_segment in result.prefix
        assert "/smoke/" not in result.prefix


class TestRequireModelApproval:
    """Tests for require_model_approval function."""

    def test_missing_approval_exits_nonzero(self, tmp_path: Path):
        """--model without APPROVAL.md exits non-zero and names both approval files."""
        # Arrange
        missing_approval = tmp_path / "missing-approval.md"

        # Act
        with patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run.APPROVAL_PATH",
            missing_approval,
        ):
            with pytest.raises(SystemExit) as exc_info:
                require_model_approval()

        # Assert
        assert exc_info.value.code != 0
        message = str(exc_info.value)
        assert COST_ESTIMATE_RELATIVE_PATH in message
        assert "experiments/ai_simulation_responses_2026_09_11/experiment2/SETUP.md" in message

    def test_existing_approval_passes(self, tmp_path: Path):
        """Approval gate passes when APPROVAL.md exists."""
        # Arrange
        approval_file = tmp_path / "APPROVAL.md"
        approval_file.write_text("approved", encoding="utf-8")

        # Act / Assert
        with patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run.APPROVAL_PATH",
            approval_file,
        ):
            require_model_approval()


class TestLoadCohortFromS3:
    """Tests for loading cohort parquet from S3 when local files are absent."""

    def test_load_cohort_users_from_s3_when_local_missing(
        self, sample_user, tmp_path: Path
    ):
        """Users load from store.get bytes when local parquet is missing."""
        # Arrange
        frame = pd.DataFrame([asdict(sample_user)])
        buffer = io.BytesIO()
        frame.to_parquet(buffer, index=False)
        parquet_bytes = buffer.getvalue()
        mock_store = MagicMock()
        mock_store.get.return_value = StoredObject(body=parquet_bytes, etag="etag")
        local_path = tmp_path / COHORT_USERS_KEY

        # Act
        with patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run.REPO_ROOT",
            tmp_path,
        ), patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run.CampaignObjectStore",
            return_value=mock_store,
        ):
            users = load_cohort_users()

        # Assert
        assert len(users) == 1
        assert users[0].prolific_id == sample_user.prolific_id
        mock_store.get.assert_called_once_with(COHORT_USERS_KEY)
        assert local_path.is_file()


class TestFullLabelPromptRendering:
    """Tests for experiment-specific full-cohort prompt rendering."""

    def test_experiment_one_has_no_participant_information(
        self, sample_user, sample_trials
    ):
        """Experiment 1 full-cohort prompts omit participant information."""
        # Act
        result = render_user_prompt(1, sample_user, sample_trials)

        # Assert
        assert "## Participant information" not in result

    def test_experiment_two_includes_participant_information(
        self, sample_user, sample_trials
    ):
        """Experiment 2 full-cohort prompts include participant information."""
        # Act
        result = render_user_prompt(2, sample_user, sample_trials)

        # Assert
        assert "## Participant information" in result
