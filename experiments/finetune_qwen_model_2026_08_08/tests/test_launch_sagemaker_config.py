"""Tests for SageMaker launcher config construction."""

from __future__ import annotations

from experiments.finetune_qwen_model_2026_08_08.launch_sagemaker import (
    INSTANCE_TYPE,
    LaunchMode,
    S3_BUCKET,
    S3_PREFIX,
    build_job_config,
)


class TestBuildJobConfig:
    """Tests for build_job_config()."""

    def test_train_paths_and_env(self):
        """Verifies train output path and required env keys."""
        # Arrange / Act
        result = build_job_config(
            mode=LaunchMode.TRAIN,
            run_id="run_test",
            role_arn="arn:aws:iam::123:role/x",
            hf_token="hf_x",
            wandb_api_key="wandb_x",
            image_uri="123.dkr.ecr.us-east-2.amazonaws.com/repo:latest",
        )

        # Assert
        assert result.instance_type == INSTANCE_TYPE == "ml.g5.xlarge"
        assert result.data_s3_uri == f"s3://{S3_BUCKET}/{S3_PREFIX}/data"
        assert (
            result.output_s3_uri
            == f"s3://{S3_BUCKET}/{S3_PREFIX}/adapters/run_test"
        )
        assert result.environment["HF_TOKEN"] == "hf_x"
        assert result.environment["WANDB_API_KEY"] == "wandb_x"
        assert result.environment["RUN_ID"] == "run_test"
        assert result.environment["ADAPTER_S3_URI"].endswith("/adapters/run_test")
        assert result.container_arguments == ["train"]

    def test_infer_baseline_pred_prefix(self):
        """Verifies baseline preds land under preds/baseline."""
        result = build_job_config(
            mode=LaunchMode.INFER_BASELINE,
            run_id="run_test",
            role_arn="arn:aws:iam::123:role/x",
            hf_token="hf_x",
            wandb_api_key=None,
            image_uri="img",
        )
        assert result.output_s3_uri.endswith("/preds/baseline")
        assert result.adapter_s3_uri is None
        assert "WANDB_API_KEY" not in result.environment
        assert result.container_arguments == ["infer_baseline"]

    def test_infer_adapter_pred_prefix(self):
        """Verifies adapter preds land under preds/fine_tuned."""
        result = build_job_config(
            mode=LaunchMode.INFER_ADAPTER,
            run_id="run_test",
            role_arn="arn:aws:iam::123:role/x",
            hf_token="hf_x",
            wandb_api_key=None,
            image_uri="img",
        )
        assert result.output_s3_uri.endswith("/preds/fine_tuned")
        assert result.adapter_s3_uri.endswith("/adapters/run_test")
        assert result.container_arguments == ["infer_adapter"]
