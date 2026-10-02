"""Immutable configuration for one Jev keep-or-remove experiment.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT"
"""

from __future__ import annotations

from dataclasses import dataclass

_SHA256_HEX_LENGTH = 64
_SHA256_HEX_DIGITS = frozenset("0123456789abcdef")
_ZERO_SHOT_EXPERIMENT_NAME = "zero_shot_jev_inference_2026_10_01"
_ZERO_SHOT_S3_BUCKET = "mirrorview-experimental-artifacts"
_ZERO_SHOT_SCHEMA_VERSION = "study2-zero-shot-jev-run-v1"
_ZERO_SHOT_PROMPT_NAME = "baseline_zero_shot_keep_remove"
_ZERO_SHOT_PROMPT_SHA256 = "bbec6228173d04e0adafa871b6dc3751cbc1e8972f29cd49d45df7ca736a46ec"
_ZERO_SHOT_INSTRUCTIONS_SHA256 = "924ad1e6a145a7e0b587ad8c5d0889c53133e6ea69f67bd64cad7b3a2214ac24"
_REQUIRED_TEXT_FIELDS = (
    "experiment_name",
    "s3_bucket",
    "s3_prefix",
    "input_records_key",
    "input_manifest_key",
    "run_manifest_schema_version",
    "prompt_name",
    "prompt_sha256",
    "instructions_sha256",
)


@dataclass(frozen=True)
class JevInferenceVariant:
    """One Jev experiment's stored paths, prompt identity, and metric exclusions."""

    experiment_name: str
    s3_bucket: str
    s3_prefix: str
    input_records_key: str
    input_manifest_key: str
    run_manifest_schema_version: str
    prompt_name: str
    prompt_sha256: str
    instructions_sha256: str
    metric_exclusion_post_ids: tuple[str, ...]

    def __post_init__(self) -> None:
        _reject_empty_text_fields(self)
        _reject_invalid_prefix(self)
        _reject_invalid_digests(self)
        _reject_duplicate_exclusions(self.metric_exclusion_post_ids)


def _reject_empty_text_fields(variant: JevInferenceVariant) -> None:
    for field_name in _REQUIRED_TEXT_FIELDS:
        if not getattr(variant, field_name):
            raise ValueError(f"{field_name} must be nonempty")


def _reject_invalid_prefix(variant: JevInferenceVariant) -> None:
    if not variant.s3_prefix.endswith("/"):
        raise ValueError("s3_prefix must end with a slash")
    _reject_key_outside_prefix(variant.input_records_key, variant.s3_prefix, "input_records_key")
    _reject_key_outside_prefix(variant.input_manifest_key, variant.s3_prefix, "input_manifest_key")


def _reject_key_outside_prefix(key: str, prefix: str, field_name: str) -> None:
    if not key.startswith(prefix):
        raise ValueError(f"{field_name} must stay under s3_prefix")


def _reject_invalid_digests(variant: JevInferenceVariant) -> None:
    _reject_invalid_digest(variant.prompt_sha256, "prompt_sha256")
    _reject_invalid_digest(variant.instructions_sha256, "instructions_sha256")


def _reject_invalid_digest(digest: str, field_name: str) -> None:
    if len(digest) != _SHA256_HEX_LENGTH or any(char not in _SHA256_HEX_DIGITS for char in digest):
        raise ValueError(f"{field_name} must be 64 lowercase hexadecimal characters")


def _reject_duplicate_exclusions(post_ids: tuple[str, ...]) -> None:
    seen: set[str] = set()
    for post_id in post_ids:
        if not post_id:
            raise ValueError("metric exclusion post id must be nonempty")
        if post_id in seen:
            raise ValueError("duplicate metric exclusion post id")
        seen.add(post_id)


ZERO_SHOT_VARIANT = JevInferenceVariant(
    experiment_name=_ZERO_SHOT_EXPERIMENT_NAME,
    s3_bucket=_ZERO_SHOT_S3_BUCKET,
    s3_prefix=f"experiments/{_ZERO_SHOT_EXPERIMENT_NAME}/",
    input_records_key=(
        "experiments/zero_shot_jev_inference_2026_10_01/inputs/"
        "study_2_five_labeler/records.jsonl"
    ),
    input_manifest_key=(
        "experiments/zero_shot_jev_inference_2026_10_01/inputs/"
        "study_2_five_labeler/manifest.json"
    ),
    run_manifest_schema_version=_ZERO_SHOT_SCHEMA_VERSION,
    prompt_name=_ZERO_SHOT_PROMPT_NAME,
    prompt_sha256=_ZERO_SHOT_PROMPT_SHA256,
    instructions_sha256=_ZERO_SHOT_INSTRUCTIONS_SHA256,
    metric_exclusion_post_ids=(),
)
