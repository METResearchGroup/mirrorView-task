"""In-memory experiment configuration for Study 2 keep or remove inference.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_llm_inference_2026_09_30.shared.config import ZERO_SHOT_VARIANT"
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

_SHA256_HEX_LENGTH = 64
_ZERO_SHOT_PROMPT_SHA256 = "bbec6228173d04e0adafa871b6dc3751cbc1e8972f29cd49d45df7ca736a46ec"
_HEX_DIGITS = frozenset("0123456789abcdef")


@dataclass(frozen=True)
class Study2InferenceVariant:
    """One Study 2 keep or remove experiment: paths, schemas, prompt, and models.

    ``model_folders`` is the ordered set of registry folders this experiment
    may run and analyze. Entries are unique nonempty tokens.
    """

    experiment_name: str
    s3_bucket: str
    s3_root: str
    input_records_s3_key: str
    input_manifest_s3_key: str
    prediction_schema_version: str
    failure_schema_version: str
    model_run_schema_version: str
    analysis_schema_version: str
    prompt_name: str
    prompt_sha256: str
    metric_exclusion_post_ids: tuple[str, ...]
    model_folders: tuple[str, ...]

    def __post_init__(self) -> None:
        _validate_variant_names(self)
        _validate_variant_locations(self)
        _validate_variant_versions(self)
        _validate_exclusion_ids(self.metric_exclusion_post_ids)
        _validate_model_folders(self.model_folders)


def _validate_variant_names(variant: Study2InferenceVariant) -> None:
    _require_token(variant.experiment_name, "experiment_name")
    _require_token(variant.prompt_name, "prompt_name")
    _require_sha256(variant.prompt_sha256)


def _validate_variant_locations(variant: Study2InferenceVariant) -> None:
    _require_token(variant.s3_bucket, "s3_bucket")
    _require_s3_root(variant.s3_root)
    _require_key_under_root(variant.input_records_s3_key, variant.s3_root, "input_records_s3_key")
    _require_key_under_root(
        variant.input_manifest_s3_key,
        variant.s3_root,
        "input_manifest_s3_key",
    )


def _validate_variant_versions(variant: Study2InferenceVariant) -> None:
    versions = (
        ("prediction_schema_version", variant.prediction_schema_version),
        ("failure_schema_version", variant.failure_schema_version),
        ("model_run_schema_version", variant.model_run_schema_version),
        ("analysis_schema_version", variant.analysis_schema_version),
    )
    for field_name, value in versions:
        _require_token(value, field_name)


def _validate_exclusion_ids(post_ids: tuple[str, ...]) -> None:
    if len(post_ids) != len(set(post_ids)):
        raise ValueError("metric_exclusion_post_ids must be unique")
    for post_id in post_ids:
        _require_token(post_id, "metric_exclusion_post_ids")


def _validate_model_folders(model_folders: tuple[str, ...]) -> None:
    if not isinstance(model_folders, tuple) or not model_folders:
        raise ValueError("model_folders must be a nonempty tuple")
    if len(model_folders) != len(set(model_folders)):
        raise ValueError("model_folders must be unique")
    for folder_name in model_folders:
        _require_token(folder_name, "model_folders")


def _require_token(value: str, field_name: str) -> None:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ValueError(f"{field_name} must be a nonempty token")


def _require_s3_root(root: str) -> None:
    _require_token(root, "s3_root")
    if not root.endswith("/") or root.startswith("/") or ".." in root.split("/"):
        raise ValueError("s3_root is invalid")


def _require_key_under_root(key: str, root: str, field_name: str) -> None:
    _require_token(key, field_name)
    if not key.startswith(root):
        raise ValueError(f"{field_name} must stay under s3_root")


def _require_sha256(value: str) -> None:
    if len(value) != _SHA256_HEX_LENGTH or any(char not in _HEX_DIGITS for char in value):
        raise ValueError("prompt_sha256 must be 64 lowercase hex characters")


def _confirmed_zero_shot_prompt_sha256() -> str:
    from experiments.zero_shot_llm_inference_2026_09_30.shared.prompts import (
        BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT,
    )

    digest = hashlib.sha256(BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT.encode("utf-8")).hexdigest()
    if digest != _ZERO_SHOT_PROMPT_SHA256:
        raise ValueError("zero-shot prompt digest drifted from the approved value")
    return _ZERO_SHOT_PROMPT_SHA256


ZERO_SHOT_VARIANT = Study2InferenceVariant(
    experiment_name="study2-zero-shot",
    s3_bucket="mirrorview-experimental-artifacts",
    s3_root="experiments/zero_shot_llm_inference_2026_09_30/",
    input_records_s3_key=(
        "experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/records.jsonl"
    ),
    input_manifest_s3_key=(
        "experiments/zero_shot_llm_inference_2026_09_30/inputs/study_2_five_labeler/manifest.json"
    ),
    prediction_schema_version="study2-zero-shot-prediction-v1",
    failure_schema_version="study2-zero-shot-failure-v1",
    model_run_schema_version="study2-zero-shot-model-run-v1",
    analysis_schema_version="study2-zero-shot-analysis-v1",
    prompt_name="BASELINE_ZERO_SHOT_KEEP_REMOVE_PROMPT",
    prompt_sha256=_confirmed_zero_shot_prompt_sha256(),
    metric_exclusion_post_ids=(),
    model_folders=(
        "amazon_nova_micro",
        "qwen3_32b",
        "openai_gpt_5_6_terra",
        "claude_sonnet_5_5",
    ),
)
