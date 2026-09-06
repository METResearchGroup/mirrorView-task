"""Immutable Parquet batch objects and the final file of a campaign feature.

Writes each completed chunk as one ``batches/part-NNNNN.parquet`` object and
writes ``final.parquet`` once every input id is labeled or recorded as failed
for good.
"""

from __future__ import annotations

import logging
from collections.abc import Collection, Mapping, Sequence
from dataclasses import dataclass
from io import BytesIO
from typing import Any

import pandas as pd
from pydantic import ValidationError

from data_platform.generate_features.models import FeatureSpec, LabelRowMetadataModel
from data_platform.generate_features.s3_feature_campaign import (
    INTERMEDIATE_ARTIFACT_TAG,
    CampaignObjectStore,
    FeaturePaths,
    append_progress,
    save_manifest,
)
from data_platform.utils.object_store import sha256_hex
from lib.timestamp_utils import get_current_timestamp

ROW_METADATA_COLUMNS = (
    "source_record_id",
    "run_id",
    "batch_id",
    "request_id",
    "attempt_count",
    "label_timestamp",
)
# Columns the feature Pydantic model already carries besides its label fields.
MODEL_IDENTITY_COLUMNS = ("source_record_id", "label_timestamp")
PROGRESS_EVENT_BATCH = "batch"
PROGRESS_EVENT_FINAL = "final"
logger = logging.getLogger(__name__)


def label_fields(spec: FeatureSpec) -> list[str]:
    """Return the feature's label columns, i.e. its model fields minus id and timestamp."""
    return [
        name for name in spec.model.model_fields if name not in MODEL_IDENTITY_COLUMNS
    ]


def campaign_row_columns(spec: FeatureSpec) -> list[str]:
    """Return the exact ordered column set of a batch object for ``spec``."""
    return [*ROW_METADATA_COLUMNS, *label_fields(spec)]


def attach_row_metadata(
    rows: list[dict[str, Any]],
    *,
    run_id: str,
    batch_id: str,
    request_ids: Mapping[str, str],
    attempt_count: int,
) -> list[dict[str, Any]]:
    """Return copies of ``rows`` with ``run_id``, ``batch_id``, ``request_id``, and ``attempt_count`` set.

    Raises
    ------
    KeyError
        When a row's ``source_record_id`` has no entry in ``request_ids``.
    """
    return [
        {
            **row,
            "run_id": run_id,
            "batch_id": batch_id,
            "request_id": request_ids[row["source_record_id"]],
            "attempt_count": attempt_count,
        }
        for row in rows
    ]


def validate_campaign_rows(rows: list[dict[str, Any]], spec: FeatureSpec, *, run_id: str) -> None:
    """Validate the label subset with ``spec.model`` and the identity columns with ``LabelRowMetadataModel``.

    Raises
    ------
    ValueError
        When a row has extra or missing columns, fails either model, carries a
        different ``run_id``, or repeats a ``source_record_id``.
    """
    expected = set(campaign_row_columns(spec))
    fields = label_fields(spec)
    seen: set[str] = set()
    for row in rows:
        columns = set(row)
        if columns != expected:
            raise ValueError(
                f"row columns {sorted(columns)} do not match the campaign column set {sorted(expected)}"
            )
        try:
            spec.model.model_validate(
                {name: row[name] for name in (*MODEL_IDENTITY_COLUMNS, *fields)}
            )
            metadata = LabelRowMetadataModel.model_validate(
                {name: row[name] for name in ROW_METADATA_COLUMNS}
            )
        except ValidationError as error:
            raise ValueError(f"invalid campaign row for {row.get('source_record_id')!r}: {error}") from error
        if metadata.run_id != run_id:
            raise ValueError(
                f"row run_id {metadata.run_id!r} does not match the campaign run_id {run_id!r}"
            )
        if metadata.source_record_id in seen:
            raise ValueError(f"duplicate source_record_id {metadata.source_record_id!r}")
        seen.add(metadata.source_record_id)


def rows_to_parquet_bytes(rows: list[dict[str, Any]], columns: Sequence[str]) -> bytes:
    """Serialize ``rows`` to Parquet with exactly ``columns`` in that order and no index."""
    frame = pd.DataFrame(rows, columns=list(columns))
    buffer = BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def parquet_rows(body: bytes) -> pd.DataFrame:
    """Read a Parquet object body back into a data frame."""
    return pd.read_parquet(BytesIO(body))


@dataclass(frozen=True)
class BatchWriteResult:
    """Where one batch object landed, its digest and row count, and the manifest ETag after recording it."""

    key: str
    sha256: str
    row_count: int
    manifest_etag: str


def _manifest_part_indexes(manifest: dict[str, Any]) -> set[int]:
    return {int(entry["part_index"]) for entry in manifest["batches"]}


def _record_batch(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    part_index: int,
    key: str,
    sha256: str,
    row_count: int,
    provider_batch_ids: list[str],
    run_id: str,
) -> BatchWriteResult:
    """Append the manifest entry for an uploaded object, save the manifest, and log progress."""
    manifest["batches"].append(
        {
            "part_index": part_index,
            "key": key,
            "row_count": row_count,
            "sha256": sha256,
            "provider_batch_ids": provider_batch_ids,
        }
    )
    manifest["batches"].sort(key=lambda entry: entry["part_index"])
    new_etag = save_manifest(store, paths, manifest, manifest_etag)
    append_progress(
        store,
        paths,
        {
            "ts": get_current_timestamp(),
            "event": PROGRESS_EVENT_BATCH,
            "run_id": run_id,
            "part_index": part_index,
            "key": key,
            "row_count": row_count,
            "sha256": sha256,
            "provider_batch_ids": provider_batch_ids,
            "rows_total": sum(int(entry["row_count"]) for entry in manifest["batches"]),
            "batches_total": len(manifest["batches"]),
        },
    )
    return BatchWriteResult(
        key=key, sha256=sha256, row_count=row_count, manifest_etag=new_etag
    )


def write_batch(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    part_index: int,
    rows: list[dict[str, Any]],
    spec: FeatureSpec,
    run_id: str,
) -> BatchWriteResult:
    """Write one immutable batch object, record it in the manifest, and append a progress line.

    The object is uploaded with ``If-None-Match: *`` and the tag
    ``intermediate-artifact=true``. The manifest entry holds the SHA-256 of
    the uploaded bytes and the distinct provider batch ids of the rows, in
    row order.

    Raises
    ------
    FileExistsError
        When ``part_index`` is already in the manifest or its key already exists.
    ValueError
        When ``rows`` is empty or fails ``validate_campaign_rows``.
    """
    if not rows:
        raise ValueError(f"refusing to write an empty batch object for part {part_index}")
    key = paths.batch_key(part_index)
    if part_index in _manifest_part_indexes(manifest):
        raise FileExistsError(f"batch part {part_index} is already recorded in the manifest")
    validate_campaign_rows(rows, spec, run_id=run_id)
    body = rows_to_parquet_bytes(rows, campaign_row_columns(spec))
    result = store.put_new(key, body, tags=INTERMEDIATE_ARTIFACT_TAG)
    provider_batch_ids = list(dict.fromkeys(str(row["batch_id"]) for row in rows))
    return _record_batch(
        store,
        paths,
        manifest,
        manifest_etag,
        part_index=part_index,
        key=key,
        sha256=result.sha256,
        row_count=len(rows),
        provider_batch_ids=provider_batch_ids,
        run_id=run_id,
    )


def adopt_unrecorded_batch(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    part_index: int,
    run_id: str,
) -> BatchWriteResult | None:
    """Record an existing batch object that a crash left out of the manifest, or return None.

    A crash between the object upload and the manifest save leaves an object
    that can never be rewritten. Adopting it hashes the stored bytes and adds
    the manifest entry, so the chunk is not labeled a second time.
    """
    if part_index in _manifest_part_indexes(manifest):
        return None
    key = paths.batch_key(part_index)
    stored = store.get(key)
    if stored is None:
        return None
    frame = parquet_rows(stored.body)
    logger.warning(
        "Adopting batch object that was missing from the manifest",
        extra={"key": key, "row_count": len(frame)},
    )
    return _record_batch(
        store,
        paths,
        manifest,
        manifest_etag,
        part_index=part_index,
        key=key,
        sha256=sha256_hex(stored.body),
        row_count=len(frame),
        provider_batch_ids=list(dict.fromkeys(frame["batch_id"].astype(str))),
        run_id=run_id,
    )


def read_batches(store: CampaignObjectStore, manifest: dict[str, Any]) -> list[pd.DataFrame]:
    """Download every manifest batch in part order, verifying each SHA-256.

    Raises
    ------
    FileNotFoundError
        When a manifest entry's object is missing.
    ValueError
        When an object's bytes do not hash to the manifest digest.
    """
    frames: list[pd.DataFrame] = []
    for entry in sorted(manifest["batches"], key=lambda item: item["part_index"]):
        stored = store.get(entry["key"])
        if stored is None:
            raise FileNotFoundError(f"manifest batch object is missing: {entry['key']}")
        digest = sha256_hex(stored.body)
        if digest != entry["sha256"]:
            raise ValueError(
                f"SHA-256 mismatch for {entry['key']}: manifest {entry['sha256']}, object {digest}"
            )
        frames.append(parquet_rows(stored.body))
    return frames


def labeled_ids(store: CampaignObjectStore, manifest: dict[str, Any]) -> set[str]:
    """Return every ``source_record_id`` held by the manifest's batch objects, verifying each digest."""
    ids: set[str] = set()
    for frame in read_batches(store, manifest):
        ids.update(frame["source_record_id"].astype(str))
    return ids


def consolidate_final(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    expected_ids: Sequence[str],
    failed_ids: Collection[str],
    spec: FeatureSpec,
    run_id: str,
) -> str | None:
    """Write ``final.parquet`` once every expected id is labeled once or has failed for good; return the new manifest ETag or None.

    Returns None without writing when the manifest already records a final
    file, when no batch object exists yet, or when some expected id is neither
    in a batch object nor in ``failed_ids``. The final file is untagged, holds
    only the labeled rows in part order, and its SHA-256 goes into the manifest
    ``final_parquet`` block together with ``row_count`` and
    ``failed_row_count``, the number of expected ids left out because they
    failed. Those two counts add up to the manifest ``expected_row_count``.

    Raises
    ------
    ValueError
        When the batch objects hold an id outside ``expected_ids`` or the same
        id twice.
    """
    if manifest.get("final_parquet"):
        return None
    frames = read_batches(store, manifest)
    if not frames:
        return None
    combined = pd.concat(frames, ignore_index=True)
    ids = combined["source_record_id"].astype(str)
    if ids.duplicated().any():
        raise ValueError("batch objects repeat a source_record_id; final.parquet not written")
    expected = set(expected_ids)
    unexpected = set(ids) - expected
    if unexpected:
        raise ValueError(
            f"batch objects hold {len(unexpected)} ids outside the input; final.parquet not written"
        )
    missing = expected - set(ids)
    if not missing.issubset(failed_ids):
        return None
    columns = campaign_row_columns(spec)
    validate_campaign_rows(combined[columns].to_dict(orient="records"), spec, run_id=run_id)
    body = rows_to_parquet_bytes(combined[columns].to_dict(orient="records"), columns)
    result = store.put_new(paths.final_key, body)
    final_record = {
        "key": paths.final_key,
        "row_count": len(combined),
        "failed_row_count": len(missing),
        "sha256": result.sha256,
    }
    manifest["final_parquet"] = final_record
    new_etag = save_manifest(store, paths, manifest, manifest_etag)
    append_progress(
        store,
        paths,
        {
            "ts": get_current_timestamp(),
            "event": PROGRESS_EVENT_FINAL,
            "run_id": run_id,
            **final_record,
        },
    )
    return new_etag
