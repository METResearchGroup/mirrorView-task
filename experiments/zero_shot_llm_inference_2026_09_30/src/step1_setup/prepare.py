"""Prepare the five-labeler Study 2 input package on S3.

Run from repo root::

    PYTHONPATH=. uv run python -m experiments.zero_shot_llm_inference_2026_09_30.src.step1_setup.prepare
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import DEFAULT_S3_REGION
from shared.data import dataloader
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)

from experiments.zero_shot_llm_inference_2026_09_30.shared.config import (
    ZERO_SHOT_VARIANT,
    Study2InferenceVariant,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.constants import (
    EXPECTED_SPLIT_RECORD_COUNT,
    EXPECTED_TOTAL_RECORD_COUNT,
    EXPECTED_UNANIMOUS_RECORD_COUNT,
    FIVE_RATER_COUNT,
    INPUT_MANIFEST_SCHEMA_VERSION,
    REMOVE_LABEL_VALUE,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import InputManifest, Study2InputRecord
from experiments.zero_shot_llm_inference_2026_09_30.shared.storage import (
    apply_lab_aws_credentials_when_unset,
    object_exists,
    parse_study2_input_jsonl_bytes,
    put_immutable_object,
    serialize_json_document,
    serialize_study2_input_jsonl,
    sha256_hex,
)

_SHARED_ROW_COLUMNS = (
    "original_text",
    "mirror_text",
    "keep_remove_label",
    "n_keep",
    "n_remove",
    "n_raters",
    "is_unanimous",
)
_SOURCE_DATASET_NAMES = (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
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


def run_setup(variant: Study2InferenceVariant) -> PreparedInputSummary:
    """Build and write the immutable input package for ``variant``.

    Raises
    ------
    ValueError
        When the registered partition or row invariants fail.
    FileExistsError
        When either immutable input object already exists.
    """
    store = _store_for_variant(variant)
    return prepare_study2_five_labeler_input(store, variant)


def copy_prepared_input(
    source: Study2InferenceVariant,
    target: Study2InferenceVariant,
) -> PreparedInputSummary:
    """Copy verified source input bytes into an empty target prefix.

    Raises
    ------
    ValueError
        When the source digest, counts, or identity do not match.
    FileExistsError
        When the target prefix is not empty.
    """
    _reject_shared_root(source, target)
    source_store = _store_for_variant(source)
    target_store = _store_for_variant(target)
    _reject_nonempty_prefix(target_store, target.s3_root)
    manifest, records_bytes = _load_source_input_bytes(source_store, source)
    _reject_unverified_source(source, manifest, records_bytes)
    _write_copied_input(target_store, target, manifest, records_bytes)
    return _summary_from_copied_manifest(target, manifest)


def prepare_study2_five_labeler_input(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant,
) -> PreparedInputSummary:
    """Load, validate, serialize, and write the immutable input package.

    Raises
    ------
    ValueError
        When the registered partition or row invariants fail.
    FileExistsError
        When either immutable input object already exists.
    """
    _ensure_input_keys_absent(store, variant)
    records = _load_and_build_records()
    records_bytes = serialize_study2_input_jsonl(records)
    manifest = build_input_manifest(records, records_bytes, variant)
    _write_input_package(store, records_bytes, manifest, variant)
    return _summary_from_records(records, manifest, variant)


def load_registered_study2_datasets() -> LoadedStudy2Datasets:
    """Load the three registered Study 2 keep/remove datasets from S3."""
    frames = [
        dataloader.load_dataset(name, low_memory=False) for name in _SOURCE_DATASET_NAMES
    ]
    return LoadedStudy2Datasets(
        all_labels=frames[0],
        unanimous_labels=frames[1],
        split_labels=frames[2],
    )


def select_five_labeler_rows(labels: pd.DataFrame) -> pd.DataFrame:
    """Return rows with exactly five labelers and unique nonempty post IDs."""
    five_labeler_rows = labels.loc[labels["n_raters"].eq(FIVE_RATER_COUNT)].copy()
    post_ids = five_labeler_rows["post_id"].astype(str)
    _reject_empty_post_ids(post_ids)
    _reject_duplicate_post_ids(post_ids)
    return five_labeler_rows


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
    all_ids = _post_id_set(all_rows)
    unanimous_ids = _post_id_set(unanimous_rows)
    split_ids = _post_id_set(split_rows)
    _reject_partition_overlap(unanimous_ids, split_ids)
    _reject_partition_union(all_ids, unanimous_ids, split_ids)
    _reject_expected_counts(all_ids, unanimous_ids, split_ids)
    _reject_row_mismatches(all_rows, unanimous_rows, unanimous_ids)
    _reject_row_mismatches(all_rows, split_rows, split_ids)


def build_study2_input_records(all_rows: pd.DataFrame) -> list[Study2InputRecord]:
    """Map registered rows to sorted ``Study2InputRecord`` objects."""
    ordered = all_rows.sort_values("post_id", kind="mergesort")
    return [_row_to_record(row) for _, row in ordered.iterrows()]


def build_input_manifest(
    records: list[Study2InputRecord],
    records_bytes: bytes,
    variant: Study2InferenceVariant,
) -> InputManifest:
    """Construct the manifest from the exact serialized JSONL bytes."""
    unanimous_count = sum(1 for record in records if record.is_unanimous)
    split_count = len(records) - unanimous_count
    return InputManifest(
        schema_version=INPUT_MANIFEST_SCHEMA_VERSION,
        source_dataset_names=_SOURCE_DATASET_NAMES,
        records_s3_key=variant.input_records_s3_key,
        records_sha256=sha256_hex(records_bytes),
        total_record_count=len(records),
        unanimous_record_count=unanimous_count,
        split_record_count=split_count,
        first_post_id=records[0].post_id,
        last_post_id=records[-1].post_id,
    )


def main() -> None:
    """CLI entrypoint for the real S3 preparation path."""
    apply_lab_aws_credentials_when_unset()
    summary = run_setup(ZERO_SHOT_VARIANT)
    print_prepared_input_summary(summary)


def print_prepared_input_summary(summary: PreparedInputSummary) -> None:
    """Print the setup success line for ``summary``."""
    print(
        f"records_key={summary.records_key} "
        f"manifest_key={summary.manifest_key} "
        f"rows={summary.row_count} "
        f"unique_post_ids={summary.unique_post_id_count} "
        f"unanimous_rows={summary.unanimous_row_count} "
        f"split_rows={summary.split_row_count}"
    )


def _ensure_input_keys_absent(
    store: CampaignObjectStore,
    variant: Study2InferenceVariant,
) -> None:
    _reject_existing_object(store, variant.input_records_s3_key)
    _reject_existing_object(store, variant.input_manifest_s3_key)


def _reject_existing_object(store: CampaignObjectStore, key: str) -> None:
    if object_exists(store, key):
        raise FileExistsError(f"Object already exists: {key}")


def _load_and_build_records() -> list[Study2InputRecord]:
    datasets = load_registered_study2_datasets()
    all_rows = select_five_labeler_rows(datasets.all_labels)
    validate_study2_partition(all_rows, datasets.unanimous_labels, datasets.split_labels)
    return build_study2_input_records(all_rows)


def _write_input_package(
    store: CampaignObjectStore,
    records_bytes: bytes,
    manifest: InputManifest,
    variant: Study2InferenceVariant,
) -> None:
    put_immutable_object(store, variant.input_records_s3_key, records_bytes)
    manifest_bytes = serialize_json_document(manifest.model_dump())
    put_immutable_object(store, variant.input_manifest_s3_key, manifest_bytes)


def _summary_from_records(
    records: list[Study2InputRecord],
    manifest: InputManifest,
    variant: Study2InferenceVariant,
) -> PreparedInputSummary:
    unanimous_rows = sum(1 for record in records if record.is_unanimous)
    split_rows = len(records) - unanimous_rows
    return PreparedInputSummary(
        records_key=variant.input_records_s3_key,
        manifest_key=variant.input_manifest_s3_key,
        row_count=len(records),
        unique_post_id_count=len({record.post_id for record in records}),
        unanimous_row_count=unanimous_rows,
        split_row_count=split_rows,
    )


def _store_for_variant(variant: Study2InferenceVariant) -> CampaignObjectStore:
    return CampaignObjectStore(variant.s3_bucket, region_name=DEFAULT_S3_REGION)


def _reject_shared_root(source: Study2InferenceVariant, target: Study2InferenceVariant) -> None:
    if source.s3_root == target.s3_root and source.s3_bucket == target.s3_bucket:
        raise ValueError("source and target experiment roots must differ")


def _reject_nonempty_prefix(store: CampaignObjectStore, prefix: str) -> None:
    if store.list_keys(prefix):
        raise FileExistsError(f"target prefix is not empty: {prefix}")


def _load_source_input_bytes(
    store: CampaignObjectStore,
    source: Study2InferenceVariant,
) -> tuple[InputManifest, bytes]:
    manifest_object = store.get(source.input_manifest_s3_key)
    records_object = store.get(source.input_records_s3_key)
    if manifest_object is None or records_object is None:
        raise ValueError("source prepared input is missing")
    manifest = InputManifest.model_validate_json(manifest_object.body)
    return manifest, records_object.body


def _reject_unverified_source(
    source: Study2InferenceVariant,
    manifest: InputManifest,
    records_bytes: bytes,
) -> None:
    if manifest.records_s3_key != source.input_records_s3_key:
        raise ValueError("source manifest records key mismatch")
    if sha256_hex(records_bytes) != manifest.records_sha256:
        raise ValueError("source records digest mismatch")
    _reject_source_record_counts(manifest, records_bytes)


def _reject_source_record_counts(manifest: InputManifest, records_bytes: bytes) -> None:
    records = parse_study2_input_jsonl_bytes(records_bytes)
    unanimous_count = sum(1 for record in records if record.is_unanimous)
    split_count = len(records) - unanimous_count
    observed = (len(records), unanimous_count, split_count)
    expected = (
        EXPECTED_TOTAL_RECORD_COUNT,
        EXPECTED_UNANIMOUS_RECORD_COUNT,
        EXPECTED_SPLIT_RECORD_COUNT,
    )
    declared = (
        manifest.total_record_count,
        manifest.unanimous_record_count,
        manifest.split_record_count,
    )
    if observed != expected or declared != expected:
        raise ValueError(f"source record counts do not match the approved input: {observed}")
    if len({record.post_id for record in records}) != len(records):
        raise ValueError("source records contain duplicate post ids")
    if records[0].post_id != manifest.first_post_id or records[-1].post_id != manifest.last_post_id:
        raise ValueError("source first or last post id mismatch")


def _write_copied_input(
    store: CampaignObjectStore,
    target: Study2InferenceVariant,
    manifest: InputManifest,
    records_bytes: bytes,
) -> None:
    copied = manifest.model_copy(update={"records_s3_key": target.input_records_s3_key})
    put_immutable_object(store, target.input_records_s3_key, records_bytes)
    manifest_bytes = serialize_json_document(copied.model_dump())
    put_immutable_object(store, target.input_manifest_s3_key, manifest_bytes)


def _summary_from_copied_manifest(
    target: Study2InferenceVariant,
    manifest: InputManifest,
) -> PreparedInputSummary:
    return PreparedInputSummary(
        records_key=target.input_records_s3_key,
        manifest_key=target.input_manifest_s3_key,
        row_count=manifest.total_record_count,
        unique_post_id_count=manifest.total_record_count,
        unanimous_row_count=manifest.unanimous_record_count,
        split_row_count=manifest.split_record_count,
    )


def _post_id_set(frame: pd.DataFrame) -> set[str]:
    return set(frame["post_id"].astype(str))


def _reject_empty_post_ids(post_ids: pd.Series) -> None:
    if post_ids.eq("").any() or post_ids.isna().any():
        raise ValueError("post_id must be nonempty")


def _reject_duplicate_post_ids(post_ids: pd.Series) -> None:
    if post_ids.duplicated().any():
        raise ValueError("duplicate post_id values are not allowed")


def _reject_partition_overlap(unanimous_ids: set[str], split_ids: set[str]) -> None:
    if unanimous_ids & split_ids:
        raise ValueError("unanimous and split post_id sets must be disjoint")


def _reject_partition_union(
    all_ids: set[str],
    unanimous_ids: set[str],
    split_ids: set[str],
) -> None:
    if all_ids != unanimous_ids | split_ids:
        raise ValueError("unanimous and split sets must cover every five-labeler post")


def _reject_expected_counts(
    all_ids: set[str],
    unanimous_ids: set[str],
    split_ids: set[str],
) -> None:
    counts = (len(all_ids), len(unanimous_ids), len(split_ids))
    expected = (
        EXPECTED_TOTAL_RECORD_COUNT,
        EXPECTED_UNANIMOUS_RECORD_COUNT,
        EXPECTED_SPLIT_RECORD_COUNT,
    )
    if counts != expected:
        raise ValueError(f"unexpected partition counts: {counts} != {expected}")


def _reject_row_mismatches(
    all_rows: pd.DataFrame,
    subset_rows: pd.DataFrame,
    subset_ids: set[str],
) -> None:
    indexed_all = _indexed_shared_columns(all_rows)
    indexed_subset = _indexed_shared_columns(subset_rows)
    for post_id in subset_ids:
        if post_id not in indexed_all.index:
            raise ValueError(f"missing post_id in all labels: {post_id}")
        if not indexed_all.loc[post_id].equals(indexed_subset.loc[post_id]):
            raise ValueError(f"row mismatch for post_id: {post_id}")


def _indexed_shared_columns(frame: pd.DataFrame) -> pd.DataFrame:
    indexed = frame.set_index(frame["post_id"].astype(str))
    return indexed.loc[:, _SHARED_ROW_COLUMNS]


def _row_to_record(row: pd.Series) -> Study2InputRecord:
    return Study2InputRecord(
        post_id=str(row["post_id"]),
        post_1_text=str(row["original_text"]),
        post_2_text=str(row["mirror_text"]),
        gold_is_remove=int(row["keep_remove_label"]) == REMOVE_LABEL_VALUE,
        n_keep=int(row["n_keep"]),
        n_remove=int(row["n_remove"]),
        n_raters=int(row["n_raters"]),
        is_unanimous=bool(row["is_unanimous"]),
    )


if __name__ == "__main__":
    main()
