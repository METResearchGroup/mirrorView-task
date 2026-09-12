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
    EXPERIMENT6_MODEL_ORDER,
    MODEL_FOLDER_BEDROCK_CLAUDE,
    MODEL_FOLDER_OPENAI,
    OUTPUT_S3_BUCKET,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import render_user_prompt
from experiments.ai_simulation_responses_2026_09_11.shared.run import (
    APPROVAL_PATH,
    COST_ESTIMATE_RELATIVE_PATH,
    EXPERIMENT2_SETUP_PATH,
    EXPERIMENT6_MODEL_CONFIGS,
    experiment6_smoke_feature_paths,
    full_feature_paths,
    load_cohort_users,
    main,
    ordered_full_input,
    require_model_approval,
    unique_pair_trials,
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
            (6, MODEL_FOLDER_OPENAI),
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
        if experiment_number == 6:
            assert "bedrock_claude" not in result.prefix


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


class TestRejectExperiment6Claude:
    """Tests for experiment 6 Claude rejection."""

    def test_main_exits_when_experiment_six_requests_claude(self):
        """--experiment 6 --model bedrock_claude exits nonzero and names Claude."""
        # Arrange / Act
        with pytest.raises(SystemExit) as exc_info:
            main(["--experiment", "6", "--model", "bedrock_claude"])

        # Assert
        assert exc_info.value.code != 0
        assert "Claude" in str(exc_info.value)


class TestOrderedFullInputExperiment6:
    """Tests for ordered_full_input experiment 6 pair grain."""

    def test_emits_twenty_unnumbered_pair_prompts(self, sample_user, sample_trials):
        """Experiment 6 emits 20 pair ids and omits Post pair headings."""
        # Arrange
        trials = []
        base = sample_trials[0]
        for pair_index in range(1, 21):
            trials.append(
                type(base)(
                    **{
                        **base.__dict__,
                        "pair_index": pair_index,
                        "post_id": f"post-{pair_index}",
                        "trial_index": pair_index - 1,
                    }
                )
            )

        # Act
        ids, texts = ordered_full_input(6, (sample_user,), {sample_user.prolific_id: trials})

        # Assert
        assert len(ids) == 20
        assert len(texts) == 20
        assert all("Post pair" not in text for text in texts.values())
        assert ids[0] == f"{sample_user.prolific_id}:1"
        assert ids[-1] == f"{sample_user.prolific_id}:20"


class TestExperiment6SmokeFeaturePaths:
    """Tests for experiment6_smoke_feature_paths function."""

    def test_prefix_is_experiment6_model_smoke(self):
        """Smoke paths land under experiment6/outputs/{model}/smoke/."""
        # Arrange
        expected_segment = "experiment6/outputs/openai/smoke/"

        # Act
        result = experiment6_smoke_feature_paths(MODEL_FOLDER_OPENAI)

        # Assert
        assert result.bucket == OUTPUT_S3_BUCKET
        assert expected_segment in result.prefix
        assert result.final_key.endswith("openai/smoke/final.parquet")
        assert "/smoke/" not in full_feature_paths(6, MODEL_FOLDER_OPENAI).final_key
        assert "bedrock_claude" not in result.prefix
        assert "experiment1/" not in result.prefix


class TestExperiment6ModelConfigs:
    """Tests for the experiment 6 three-model loop."""

    def test_excludes_claude(self):
        """Experiment 6 smoke configs are the three non-Claude models."""
        # Arrange
        folders = [config[0] for config in EXPERIMENT6_MODEL_CONFIGS]

        # Act / Assert
        assert tuple(folders) == EXPERIMENT6_MODEL_ORDER
        assert MODEL_FOLDER_BEDROCK_CLAUDE not in folders


class TestUniquePairTrials:
    """Tests for unique_pair_trials function."""

    def test_keeps_earliest_trial_for_duplicate_pair_index(self, sample_trials):
        """Duplicate pair_index rows keep the earliest trial_index."""
        # Arrange
        first = sample_trials[0]
        later = type(first)(
            **{**first.__dict__, "trial_index": 99, "original_text": "later-copy"}
        )

        # Act
        result = unique_pair_trials([later, first])

        # Assert
        assert len(result) == 1
        assert result[0].original_text == first.original_text
        assert result[0].trial_index == first.trial_index


class TestExperiment6SmokeDispatch:
    """Tests for experiment 6 --smoke and --estimate-cost dispatch."""

    def test_smoke_calls_experiment6_path_not_experiment1(self):
        """experiment6/run.py --smoke does not invoke the experiment 1 smoke loop."""
        # Arrange
        with patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run."
            "experiment6_smoke_command"
        ) as experiment6_smoke, patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run.smoke_command"
        ) as experiment1_smoke:
            # Act
            main(["--experiment", "6", "--smoke"])

        # Assert
        experiment6_smoke.assert_called_once()
        experiment1_smoke.assert_not_called()

    def test_estimate_cost_calls_experiment6_path_not_parent(self):
        """experiment6 --estimate-cost does not write the parent cost file."""
        # Arrange
        with patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run."
            "experiment6_estimate_cost_command"
        ) as experiment6_cost, patch(
            "experiments.ai_simulation_responses_2026_09_11.shared.run."
            "estimate_cost_command"
        ) as parent_cost:
            # Act
            main(["--experiment", "6", "--estimate-cost"])

        # Assert
        experiment6_cost.assert_called_once()
        parent_cost.assert_not_called()


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
