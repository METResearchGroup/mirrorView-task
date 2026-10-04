"""Copy the verified zero-shot Jev input into the optimized-prompt prefix.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.few_shot_jev_optimized_prompt_2026_10_04.src.step1_setup.main
"""

from __future__ import annotations

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.few_shot_jev_optimized_prompt_2026_10_04.shared.config import OPTIMIZED_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.shared.config import ZERO_SHOT_VARIANT
from experiments.zero_shot_jev_inference_2026_10_01.src.step1_setup.prepare import (
    copy_prepared_input,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import InputManifest
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
)


def main() -> None:
    """Copy the prepared input and print one summary line."""
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(OPTIMIZED_VARIANT.s3_bucket)
    manifest = copy_prepared_input(store, source=ZERO_SHOT_VARIANT, target=OPTIMIZED_VARIANT)
    print(_summary_line(manifest))


def _summary_line(manifest: InputManifest) -> str:
    return (
        f"records_key={manifest.records_s3_key} "
        f"manifest_key={OPTIMIZED_VARIANT.input_manifest_key} "
        f"rows={manifest.total_record_count} unique_post_ids={manifest.total_record_count} "
        f"unanimous_rows={manifest.unanimous_record_count} "
        f"split_rows={manifest.split_record_count} sha256={manifest.records_sha256}"
    )


if __name__ == "__main__":
    main()
