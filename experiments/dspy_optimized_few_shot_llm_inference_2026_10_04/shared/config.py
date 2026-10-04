"""Optimized few-shot Study 2 paths, schema versions, and prompt identity.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.dspy_optimized_few_shot_llm_inference_2026_10_04.shared.config import OPTIMIZED_FEW_SHOT_VARIANT"
"""

from __future__ import annotations

import hashlib

from experiments.zero_shot_llm_inference_2026_09_30.shared.config import Study2InferenceVariant
from shared.models.llm.prompt import OPTIMIZED_STUDY_PROMPT_TEMPLATE

_OPTIMIZED_PROMPT_SHA256 = "6ebcd9bbb16ff39dbeba93fe832a601a589ce1d8233645aad5030b105df9af15"
_S3_ROOT = "experiments/dspy_optimized_few_shot_llm_inference_2026_10_04/"
_METRIC_EXCLUSION_POST_IDS = (
    "bluesky_0bd24d995926c0a58ee7129aa11cb44919170f35e9d51c137745334333c17cd7",
    "bluesky_0e8a5a0e2e218f117502ba8bb6c697977992905462970a1c2c0773a22ea2888c",
    "bluesky_007568ddfadcb450bb8b91253a673315384eb1d5ca9f9886462eb722ea5c2b48",
    "bluesky_00a60cda611def7235d1ac6d87c60320703653e74fb39204a819ec86d6db680b",
    "bluesky_00efc34ac2738154e7f93b9e110637107b810be4ae2173e8657241f3d1fdd206",
)


def _confirmed_optimized_prompt_sha256() -> str:
    digest = hashlib.sha256(OPTIMIZED_STUDY_PROMPT_TEMPLATE.encode("utf-8")).hexdigest()
    if digest != _OPTIMIZED_PROMPT_SHA256:
        raise ValueError("optimized prompt digest drifted from the approved value")
    return _OPTIMIZED_PROMPT_SHA256


OPTIMIZED_FEW_SHOT_VARIANT = Study2InferenceVariant(
    experiment_name="study2-dspy-optimized-few-shot",
    s3_bucket="mirrorview-experimental-artifacts",
    s3_root=_S3_ROOT,
    input_records_s3_key=f"{_S3_ROOT}inputs/study_2_five_labeler/records.jsonl",
    input_manifest_s3_key=f"{_S3_ROOT}inputs/study_2_five_labeler/manifest.json",
    prediction_schema_version="study2-dspy-optimized-few-shot-prediction-v1",
    failure_schema_version="study2-dspy-optimized-few-shot-failure-v1",
    model_run_schema_version="study2-dspy-optimized-few-shot-model-run-v1",
    analysis_schema_version="study2-dspy-optimized-few-shot-analysis-v1",
    prompt_name="OPTIMIZED_STUDY_PROMPT_TEMPLATE",
    prompt_sha256=_confirmed_optimized_prompt_sha256(),
    metric_exclusion_post_ids=_METRIC_EXCLUSION_POST_IDS,
    model_folders=("amazon_nova_micro", "qwen3_32b"),
)
