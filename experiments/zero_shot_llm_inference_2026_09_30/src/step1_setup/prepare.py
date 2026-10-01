"""Prepare the five-labeler Study 2 input package on S3.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

from dataclasses import dataclass

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore

from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import InputManifest, Study2InputRecord
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    put_immutable_object,
    serialize_study2_input_jsonl,
)


@dataclass(frozen=True)
class PreparedInputSummary:
    """Counts emitted by a successful preparation run."""

    records_key: str
    manifest_key: str
    row_count: int
    unique_post_id_count: int
    unanimous_row_count: int
    split_row_count: int


def prepare_study2_five_labeler_input(
    store: CampaignObjectStore,
) -> PreparedInputSummary:
    """Load, validate, serialize, and write the immutable input package."""
    records = _load_and_build_records()
    records_bytes = serialize_study2_input_jsonl(records)
    manifest = _build_manifest(records, records_bytes)
    _write_input_package(store, records_bytes, manifest)
    return _summary_from_records(records, manifest)


def main() -> None:
    """CLI entrypoint for the real S3 preparation path."""
    apply_lab_aws_credentials_when_unset()
    store = _build_campaign_store()
    summary = prepare_study2_five_labeler_input(store)
    _print_success(summary)


def _load_and_build_records() -> list[Study2InputRecord]:
    raise NotImplementedError


def _build_manifest(
    records: list[Study2InputRecord],
    records_bytes: bytes,
) -> InputManifest:
    raise NotImplementedError


def _write_input_package(
    store: CampaignObjectStore,
    records_bytes: bytes,
    manifest: InputManifest,
) -> None:
    put_immutable_object(store, "", records_bytes)
    put_immutable_object(store, "", b"")


def _build_campaign_store() -> CampaignObjectStore:
    raise NotImplementedError


def _summary_from_records(
    records: list[Study2InputRecord],
    manifest: InputManifest,
) -> PreparedInputSummary:
    raise NotImplementedError


def _print_success(summary: PreparedInputSummary) -> None:
    print(
        f"records_key={summary.records_key} "
        f"manifest_key={summary.manifest_key} "
        f"rows={summary.row_count} "
        f"unique_post_ids={summary.unique_post_id_count} "
        f"unanimous_rows={summary.unanimous_row_count} "
        f"split_rows={summary.split_row_count}"
    )


if __name__ == "__main__":
    main()
