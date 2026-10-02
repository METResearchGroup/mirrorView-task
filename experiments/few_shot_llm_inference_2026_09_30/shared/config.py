"""Few-shot Study 2 experiment paths, schema versions, and prompt identity.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_llm_inference_2026_09_30.shared.config import FEW_SHOT_VARIANT"
"""

from __future__ import annotations

import hashlib

from experiments.few_shot_llm_inference_2026_09_30.shared.prompts import (
    BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.config import Study2InferenceVariant

_FEW_SHOT_PROMPT_SHA256 = "ca6f0df53ad3a39136d1d9794ea73cfb6f8171ff1b5eb22e0d45e3d92e164fe3"
_S3_ROOT = "experiments/few_shot_llm_inference_2026_09_30/"
_METRIC_EXCLUSION_POST_IDS = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)


def _confirmed_few_shot_prompt_sha256() -> str:
    digest = hashlib.sha256(BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT.encode("utf-8")).hexdigest()
    if digest != _FEW_SHOT_PROMPT_SHA256:
        raise ValueError("few-shot prompt digest drifted from the approved value")
    return _FEW_SHOT_PROMPT_SHA256


FEW_SHOT_VARIANT = Study2InferenceVariant(
    experiment_name="study2-few-shot",
    s3_bucket="mirrorview-experimental-artifacts",
    s3_root=_S3_ROOT,
    input_records_s3_key=f"{_S3_ROOT}inputs/study_2_five_labeler/records.jsonl",
    input_manifest_s3_key=f"{_S3_ROOT}inputs/study_2_five_labeler/manifest.json",
    prediction_schema_version="study2-few-shot-prediction-v1",
    failure_schema_version="study2-few-shot-failure-v1",
    model_run_schema_version="study2-few-shot-model-run-v1",
    analysis_schema_version="study2-few-shot-analysis-v1",
    prompt_name="BASELINE_FEW_SHOT_KEEP_REMOVE_PROMPT",
    prompt_sha256=_confirmed_few_shot_prompt_sha256(),
    metric_exclusion_post_ids=_METRIC_EXCLUSION_POST_IDS,
)
