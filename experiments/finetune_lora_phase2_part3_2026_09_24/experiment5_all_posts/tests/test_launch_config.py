"""Tests for experiment5 SageMaker launcher dry-run configuration."""

from __future__ import annotations

from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import (
    ADAPTER_S3_URIS,
    DATA_S3_URI,
    ECR_IMAGE_URI,
    merged_model_s3_uri,
    preds_s3_uri,
)
from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.launch_sagemaker import (
    build_job_config,
)

_ROLE = "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
_HF = "hf_test_token"


class TestBuildJobConfig:
    """Frozen URI checks without AWS STS."""

    def test_merge_unanimous_adapter_and_merged_output(self) -> None:
        config = build_job_config(
            mode="merge",
            model_variant="unanimous",
            role_arn=_ROLE,
            hf_token=_HF,
            image_uri=ECR_IMAGE_URI,
        )
        assert config.data_s3_uri == DATA_S3_URI
        assert config.adapter_s3_uri == ADAPTER_S3_URIS["unanimous"]
        assert config.output_s3_uri == merged_model_s3_uri("unanimous")
        assert config.container_arguments == ["merge"]
        assert config.image_uri.endswith(":vllm-all-posts")

    def test_infer_modal_merged_channel_and_preds_env(self) -> None:
        config = build_job_config(
            mode="infer",
            model_variant="modal",
            role_arn=_ROLE,
            hf_token=_HF,
            image_uri=ECR_IMAGE_URI,
        )
        assert config.merged_s3_uri == merged_model_s3_uri("modal")
        assert config.preds_s3_uri == preds_s3_uri("modal")
        assert config.environment["PREDS_S3_URI"] == preds_s3_uri("modal")
        assert config.adapter_s3_uri is None
        assert config.container_arguments == ["infer"]
