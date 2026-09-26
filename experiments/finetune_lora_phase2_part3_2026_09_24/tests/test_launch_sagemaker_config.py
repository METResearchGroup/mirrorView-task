"""Tests for Part 3 SageMaker launcher config construction."""

from __future__ import annotations

import json

import pytest

from experiments.finetune_lora_phase2_part3_2026_09_24.launch_sagemaker import (
    S3_BUCKET,
    S3_PREFIX,
    build_job_config,
)
from experiments.finetune_qwen_model_2026_08_08.launch_sagemaker import LaunchMode

_ROLE = "arn:aws:iam::123:role/x"
_IMAGE = "123.dkr.ecr.us-east-2.amazonaws.com/mirrorview-finetune-lora-phase2-part3:latest"
_HF = "hf_test"
_WANDB = "wandb_test"


class TestBuildJobConfig:
    """Tests for build_job_config()."""

    def test_train_experiment1_paths_and_env(self) -> None:
        """Verifies train data/output paths and thinking-disabled env."""
        # Act
        result = build_job_config(
            mode=LaunchMode.TRAIN,
            experiment="experiment1_unanimous",
            run_id="part3_smoke_001",
            role_arn=_ROLE,
            hf_token=_HF,
            wandb_api_key=_WANDB,
            image_uri=_IMAGE,
        )

        # Assert
        assert result.data_s3_uri.endswith("experiment1_unanimous/data")
        assert result.output_s3_uri.endswith(
            "experiment1_unanimous/adapters/part3_smoke_001"
        )
        template_json = result.environment["CHAT_TEMPLATE_KWARGS_JSON"]
        assert json.loads(template_json)["enable_thinking"] is False

    def test_infer_adapter_experiment1_paths(self) -> None:
        """Verifies infer_adapter adapter channel and preds output."""
        # Act
        result = build_job_config(
            mode=LaunchMode.INFER_ADAPTER,
            experiment="experiment1_unanimous",
            run_id="part3_uni_001",
            role_arn=_ROLE,
            hf_token=_HF,
            wandb_api_key=None,
            image_uri=_IMAGE,
        )

        # Assert
        assert result.adapter_s3_uri is not None
        assert result.adapter_s3_uri.endswith(
            "experiment1_unanimous/adapters/part3_uni_001"
        )
        assert result.output_s3_uri.endswith("experiment1_unanimous/preds")

    def test_train_experiment4_raises(self) -> None:
        """Verifies train rejects experiment4_cross_eval."""
        with pytest.raises(ValueError):
            build_job_config(
                mode=LaunchMode.TRAIN,
                experiment="experiment4_cross_eval",
                run_id="part3_smoke_001",
                role_arn=_ROLE,
                hf_token=_HF,
                wandb_api_key=_WANDB,
                image_uri=_IMAGE,
            )

    def test_infer_adapter_experiment4_raises(self) -> None:
        """Verifies infer_adapter rejects experiment4_cross_eval."""
        with pytest.raises(ValueError):
            build_job_config(
                mode=LaunchMode.INFER_ADAPTER,
                experiment="experiment4_cross_eval",
                run_id="part3_uni_001",
                role_arn=_ROLE,
                hf_token=_HF,
                wandb_api_key=None,
                image_uri=_IMAGE,
            )

    def test_infer_baseline_experiment1_raises(self) -> None:
        """Verifies infer_baseline rejects experiments 1 through 3."""
        with pytest.raises(ValueError):
            build_job_config(
                mode=LaunchMode.INFER_BASELINE,
                experiment="experiment1_unanimous",
                run_id="part3_smoke_001",
                role_arn=_ROLE,
                hf_token=_HF,
                wandb_api_key=None,
                image_uri=_IMAGE,
            )

    def test_infer_baseline_experiment4_paths(self) -> None:
        """Verifies infer_baseline only allows experiment4 preds output."""
        # Act
        result = build_job_config(
            mode=LaunchMode.INFER_BASELINE,
            experiment="experiment4_cross_eval",
            run_id="part3_smoke_001",
            role_arn=_ROLE,
            hf_token=_HF,
            wandb_api_key=None,
            image_uri=_IMAGE,
        )

        # Assert
        assert result.data_s3_uri == f"s3://{S3_BUCKET}/{S3_PREFIX}/data"
        assert result.output_s3_uri.endswith("experiment4_cross_eval/preds")
