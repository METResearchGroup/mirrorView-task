"""Optimized-prompt Jev paths, prompt digests, and metric exclusions.

Run from repo root::

    PYTHONPATH=. uv run python -c "from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT"
"""

from __future__ import annotations

from experiments.zero_shot_jev_inference_2026_10_01.shared.config import JevInferenceVariant

_PLACEHOLDER_DIGEST = "0" * 64

OPTIMIZED_VARIANT = JevInferenceVariant(
    experiment_name="placeholder",
    s3_bucket="placeholder",
    s3_prefix="experiments/placeholder/",
    input_records_key="experiments/placeholder/records.jsonl",
    input_manifest_key="experiments/placeholder/manifest.json",
    run_manifest_schema_version="placeholder",
    prompt_name="placeholder",
    prompt_sha256=_PLACEHOLDER_DIGEST,
    instructions_sha256=_PLACEHOLDER_DIGEST,
    metric_exclusion_post_ids=(),
)
