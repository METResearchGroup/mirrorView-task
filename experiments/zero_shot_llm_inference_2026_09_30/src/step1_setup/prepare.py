"""Prepare the five-labeler Study 2 input package on S3.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import DEFAULT_S3_REGION

from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPERIMENT_S3_BUCKET,
    INPUT_MANIFEST_KEY,
    INPUT_RECORDS_KEY,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import InputManifest, Study2InputRecord
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    object_exists,
    put_immutable_object,
    serialize_json_document,
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


@dataclass(frozen=True)
class LoadedStudy2Datasets:
    """Registered Study 2 frames used to build the input package."""

    all_labels: pd.DataFrame
    unanimous_labels: pd.DataFrame
    split_labels: pd.DataFrame


def prepare_study2_five_labeler_input(
    store: CampaignObjectStore,
) -> PreparedInputSummary:
    """Load, validate, serialize, and write the immutable input package.

    Raises
    ------
    ValueError
        When the registered partition or row invariants fail.
    FileExistsError
        When either immutable input object already exists.
    """
    _ensure_input_keys_absent(store)
    records = _load_and_build_records()
    records_bytes = serialize_study2_input_jsonl(records)
    manifest = _build_manifest(records, records_bytes)
    _write_input_package(store, records_bytes, manifest)
    return _summary_from_records(records, manifest)


def load_registered_study2_datasets() -> LoadedStudy2Datasets:
    """Load the three registered Study 2 keep/remove datasets from S3."""
    raise NotImplementedError


def select_five_labeler_rows(labels: pd.DataFrame) -> pd.DataFrame:
    """Return rows with exactly five labelers and unique nonempty post IDs."""
    raise NotImplementedError


def validate_study2_partition(
    all_rows: pd.DataFrame,
    unanimous_rows: pd.DataFrame,
    split_rows: pd.DataFrame,
) -> None:
    """Reject overlapping or incomplete unanimous and split partitions.

    Raises
    ------
    ValueError
        When the partition invariants fail.
    """
    raise NotImplementedError


def build_study2_input_records(all_rows: pd.DataFrame) -> list[Study2InputRecord]:
    """Map registered rows to sorted ``Study2InputRecord`` objects."""
    raise NotImplementedError


def build_input_manifest(
    records: list[Study2InputRecord],
    records_bytes: bytes,
) -> InputManifest:
    """Construct the manifest from the exact serialized JSONL bytes."""
    raise NotImplementedError


def main() -> None:
    """CLI entrypoint for the real S3 preparation path."""
    apply_lab_aws_credentials_when_unset()
    store = CampaignObjectStore(EXPERIMENT_S3_BUCKET, region_name=DEFAULT_S3_REGION)
    summary = prepare_study2_five_labeler_input(store)
    _print_success(summary)


def _ensure_input_keys_absent(store: CampaignObjectStore) -> None:
    raise NotImplementedError


def _load_and_build_records() -> list[Study2InputRecord]:
    datasets = load_registered_study2_datasets()
    all_rows = select_five_labeler_rows(datasets.all_labels)
    validate_study2_partition(all_rows, datasets.unanimous_labels, datasets.split_labels)
    return build_study2_input_records(all_rows)


def _build_manifest(
    records: list[Study2InputRecord],
    records_bytes: bytes,
) -> InputManifest:
    return build_input_manifest(records, records_bytes)


def _write_input_package(
    store: CampaignObjectStore,
    records_bytes: bytes,
    manifest: InputManifest,
) -> None:
    raise NotImplementedError


def _summary_from_records(
    records: list[Study2InputRecord],
    manifest: InputManifest,
) -> PreparedInputSummary:
    unanimous_rows = sum(1 for record in records if record.is_unanimous)
    split_rows = len(records) - unanimous_rows
    return PreparedInputSummary(
        records_key=INPUT_RECORDS_KEY,
        manifest_key=INPUT_MANIFEST_KEY,
        row_count=len(records),
        unique_post_id_count=len({record.post_id for record in records}),
        unanimous_row_count=unanimous_rows,
        split_row_count=split_rows,
    )


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
