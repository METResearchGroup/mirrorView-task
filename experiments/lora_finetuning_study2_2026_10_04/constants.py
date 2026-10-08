"""Shared Study 2 LoRA experiment constants (no training stack imports)."""

from __future__ import annotations

from urllib.parse import urlparse

MODEL_NAME = "Qwen/Qwen3.5-4B"
# Rank 128 and a learning rate above the full fine-tuning default, from the
# TRL SFT LoRA guide. LORA_ALPHA stays in train.py.
LORA_RANK = 128
# Qwen3.5 alternates full attention and Gated DeltaNet linear attention, then
# an MLP. The depthwise conv inside linear attention is a grouped Conv1d
# (groups=8192). PEFT only wraps that layer when rank is divisible by the
# group count, and rank 128 is not, so conv1d stays frozen. The names below
# cover both attention families and the MLP.
LORA_TARGET_MODULES = [
    "q_proj",
    "k_proj",
    "v_proj",
    "o_proj",
    "in_proj_qkv",
    "in_proj_z",
    "in_proj_b",
    "in_proj_a",
    "out_proj",
    "gate_proj",
    "up_proj",
    "down_proj",
]
# The optimized study prompt is about 1.5k tokens before the two posts.
# 4096 leaves room for the posts and keeps the completion inside the sequence.
MAX_LENGTH = 4096

ARTIFACTS_BUCKET = "mirrorview-experimental-artifacts"
ADAPTER_S3_PREFIX = "experiments/lora_finetuning_study2_2026_10_04/adapters"


def parse_s3_uri(uri: str) -> tuple[str, str]:
    """Split ``s3://bucket/prefix`` into bucket and key prefix."""
    parsed = urlparse(uri)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Invalid S3 URI: {uri}")
    bucket = parsed.netloc
    prefix = parsed.path.lstrip("/").rstrip("/")
    return bucket, prefix


def build_adapter_s3_uri(group: str, run_name: str) -> str:
    """Return the S3 prefix where this run's LoRA adapter is stored."""
    return f"s3://{ARTIFACTS_BUCKET}/{ADAPTER_S3_PREFIX}/{group}/{run_name}/"
