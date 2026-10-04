"""Few-shot Jev experiment paths, prompt digests, and metric exclusions.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_inference_2026_10_01.shared.config import FEW_SHOT_VARIANT"
"""

from __future__ import annotations

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import JevInferenceVariant

_EXPERIMENT_NAME = "few_shot_jev_inference_2026_10_01"
_S3_BUCKET = "mirrorview-experimental-artifacts"
_S3_PREFIX = f"experiments/{_EXPERIMENT_NAME}/"
_INPUT_DIR = f"{_S3_PREFIX}inputs/study_2_five_labeler/"
_SCHEMA_VERSION = "study2-few-shot-jev-run-v1"
_PROMPT_NAME = "baseline_few_shot_keep_remove"
_PROMPT_SHA256 = "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
_INSTRUCTIONS_SHA256 = "a455405fd838ef17205e15652ede24dd237d679e6ab8bbf52233ee691893dfac"
_METRIC_EXCLUSION_POST_IDS = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)

FEW_SHOT_VARIANT = JevInferenceVariant(
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
