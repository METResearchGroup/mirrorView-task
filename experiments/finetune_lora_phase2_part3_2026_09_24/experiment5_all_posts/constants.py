"""Frozen constants for experiment5 all-posts vLLM inference.

Run from root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.finetune_lora_phase2_part3_2026_09_24.experiment5_all_posts.constants import MODEL_ID; print(MODEL_ID)"
"""

from __future__ import annotations

from typing import Final, Literal

ModelVariant = Literal["unanimous", "modal"]
LaunchModeName = Literal["merge", "infer"]

MODEL_ID: Final[str] = "Qwen/Qwen3.5-4B"
CHAT_TEMPLATE_KWARGS: Final[dict[str, bool]] = {"enable_thinking": False}

S3_BUCKET: Final[str] = "mirrorview-experimental-artifacts"
PART3_S3_PREFIX: Final[str] = "experiments/finetune_lora_phase2_part3_2026_09_24"
EXPERIMENT5_S3_PREFIX: Final[str] = f"{PART3_S3_PREFIX}/experiment5_all_posts"

AWS_REGION: Final[str] = "us-east-2"
INSTANCE_TYPE: Final[str] = "ml.g5.xlarge"
SAGEMAKER_ROLE_ARN: Final[str] = (
    "arn:aws:iam::517478598677:role/mirrorview-qwen-finetune-sm-exec"
)
ECR_IMAGE_URI: Final[str] = (
    "517478598677.dkr.ecr.us-east-2.amazonaws.com/"
    "mirrorview-finetune-lora-phase2-part3:vllm-all-posts"
)

ADAPTER_S3_URIS: Final[dict[ModelVariant, str]] = {
    "unanimous": (
        f"s3://{S3_BUCKET}/{PART3_S3_PREFIX}/"
        "experiment1_unanimous/adapters/part3_uni_001"
    ),
    "modal": (
        f"s3://{S3_BUCKET}/{PART3_S3_PREFIX}/"
        "experiment2_modal/adapters/part3_modal_001"
    ),
}

DATA_S3_URI: Final[str] = f"s3://{S3_BUCKET}/{EXPERIMENT5_S3_PREFIX}/data"

MERGED_MODEL_SUBDIRS: Final[dict[ModelVariant, str]] = {
    "unanimous": "merged_models/unanimous_model",
    "modal": "merged_models/modal_model",
}

PREDS_SUBDIRS: Final[dict[ModelVariant, str]] = {
    "unanimous": "preds/unanimous_model",
    "modal": "preds/modal_model",
}

CHAT_JSONL_FILENAME: Final[str] = "chat_all_posts.jsonl"
OUTPUT_CSV_FILENAME: Final[str] = "all_posts.csv"

CHUNK_SIZE: Final[int] = 32

VLLM_DTYPE: Final[str] = "bfloat16"
VLLM_MAX_MODEL_LEN: Final[int] = 10240
VLLM_GPU_MEMORY_UTILIZATION: Final[float] = 0.90
VLLM_MAX_NUM_SEQS: Final[int] = 32
VLLM_ENABLE_PREFIX_CACHING: Final[bool] = True
VLLM_TRUST_REMOTE_CODE: Final[bool] = True

SAMPLING_TEMPERATURE: Final[float] = 0.0
SAMPLING_MAX_TOKENS: Final[int] = 8

PRED_COLUMNS: Final[tuple[str, ...]] = (
    "message_id",
    "decision",
    "keep_remove_label",
    "raw_generation",
    "predicted_decision",
    "predicted_label",
)

CONTAINER_ENTRY_POINT: Final[tuple[str, ...]] = (
    "/app/experiments/finetune_lora_phase2_part3_2026_09_24/"
    "experiment5_all_posts/entrypoint.sh",
)


def merged_model_s3_uri(variant: ModelVariant) -> str:
    """Return S3 prefix for a merged model directory."""
    subdir = MERGED_MODEL_SUBDIRS[variant]
    return f"s3://{S3_BUCKET}/{EXPERIMENT5_S3_PREFIX}/{subdir}"


def preds_s3_uri(variant: ModelVariant) -> str:
    """Return S3 prefix for prediction outputs."""
    subdir = PREDS_SUBDIRS[variant]
    return f"s3://{S3_BUCKET}/{EXPERIMENT5_S3_PREFIX}/{subdir}"
