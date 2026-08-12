"""Tests for comparison SageMaker job config."""

from __future__ import annotations

from experiments.compare_qwen_lora_modal_eval_2026_08_12.launch_sagemaker import (
    ADAPTER_S3_URI,
    ECR_REPO_NAME,
    PREDS_S3_URI,
    build_job_config,
)


def test_build_job_config_points_at_unanimous_adapter_and_preds() -> None:
    """Dry-run config mounts unanimous adapter and writes unanimous preds."""
    config = build_job_config(
        run_id="compare_dry",
        role_arn="arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec",
        hf_token="hf_test",
        image_uri=(
            f"517478598677.dkr.ecr.us-east-2.amazonaws.com/"
            f"{ECR_REPO_NAME}:latest"
        ),
    )
    assert config.adapter_s3_uri == ADAPTER_S3_URI
    assert config.adapter_s3_uri.endswith(
        "adapters/unanimous_passrole_probe3_lean"
    )
    assert config.output_s3_uri == PREDS_S3_URI
    assert config.output_s3_uri.endswith("preds/unanimous_lora")
    assert config.environment["PREDS_S3_URI"] == PREDS_S3_URI
    assert config.data_s3_uri.endswith(
        "mirrorview-larger_finetune_qwen_model_2026_08_08/data"
    )
    assert ECR_REPO_NAME in config.image_uri
    assert config.container_arguments == ["infer_adapter"]
