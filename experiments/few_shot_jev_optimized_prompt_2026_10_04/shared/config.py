"""Optimized-prompt Jev paths, prompt digests, and metric exclusions.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT"
"""

from __future__ import annotations

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import JevInferenceVariant

_EXPERIMENT_NAME = "few_shot_jev_optimized_prompt_2026_10_04"
_S3_BUCKET = "mirrorview-experimental-artifacts"
_S3_PREFIX = f"experiments/{_EXPERIMENT_NAME}/"
_INPUT_DIR = f"{_S3_PREFIX}inputs/study_2_five_labeler/"
_SCHEMA_VERSION = "study2-optimized-prompt-jev-run-v1"
_PROMPT_NAME = "optimized_study_prompt"
_PROMPT_SHA256 = "178535e42f301a17be4fdcee23cf4abb53f637365cfc1cb673326de9c471bf7f"
_INSTRUCTIONS_SHA256 = "1929e49a31c20488ff25a134d53d9e267d7214ca723575042ef6d7a19f23cb5e"
_METRIC_EXCLUSION_POST_IDS = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)

OPTIMIZED_VARIANT = JevInferenceVariant(
    experiment_name=_EXPERIMENT_NAME,
    s3_bucket=_S3_BUCKET,
    s3_prefix=_S3_PREFIX,
    input_records_key=f"{_INPUT_DIR}records.jsonl",
    input_manifest_key=f"{_INPUT_DIR}manifest.json",
    run_manifest_schema_version=_SCHEMA_VERSION,
    prompt_name=_PROMPT_NAME,
    prompt_sha256=_PROMPT_SHA256,
    instructions_sha256=_INSTRUCTIONS_SHA256,
    metric_exclusion_post_ids=_METRIC_EXCLUSION_POST_IDS,
)
