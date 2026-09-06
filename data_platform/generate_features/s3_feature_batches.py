"""Immutable Parquet batch objects and the final consolidated file of a campaign feature.

Adds the Q44 provenance columns to label rows, validates the label subset and
the provenance columns separately, writes one ``batches/part-NNNNN.parquet``
object per completed chunk, and consolidates ``final.parquet`` once every
input id has a row.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import pandas as pd

from data_platform.generate_features.models import FeatureSpec
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
)

PROVENANCE_COLUMNS = (
    "source_record_id",
    "run_id",
    "batch_id",
    "request_id",
    "attempt_count",
    "label_timestamp",
)


def label_fields(spec: FeatureSpec) -> list[str]:
    """Return the feature's label columns, i.e. its model fields minus id and timestamp."""
    raise NotImplementedError


def q44_columns(spec: FeatureSpec) -> list[str]:
    """Return the exact ordered column set of a batch object for ``spec``."""
    raise NotImplementedError


def attach_provenance(
    rows: list[dict[str, Any]],
    *,
    run_id: str,
    batch_id: str,
    request_ids: Mapping[str, str],
    attempt_count: int,
) -> list[dict[str, Any]]:
    """Return copies of ``rows`` with ``run_id``, ``batch_id``, ``request_id``, and ``attempt_count`` set."""
    raise NotImplementedError


def validate_q44_rows(rows: list[dict[str, Any]], spec: FeatureSpec, *, run_id: str) -> None:
    """Validate the label subset with ``spec.model`` and the provenance columns with ``Q44ProvenanceModel``.

    Raises
    ------
    ValueError
        When a row has extra or missing columns, fails either model, carries a
        different ``run_id``, or repeats a ``source_record_id``.
    """
    raise NotImplementedError


def rows_to_parquet_bytes(rows: list[dict[str, Any]], columns: Sequence[str]) -> bytes:
    raise NotImplementedError


def parquet_rows(body: bytes) -> pd.DataFrame:
    raise NotImplementedError


@dataclass(frozen=True)
class BatchWriteResult:
    key: str
    sha256: str
    row_count: int
    manifest_etag: str


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

    Raises
    ------
    FileExistsError
        When ``part_index`` is already in the manifest or its key already exists.
    """
    raise NotImplementedError


def adopt_unrecorded_batch(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    part_index: int,
    run_id: str,
) -> BatchWriteResult | None:
    """Record an existing batch object that a crash left out of the manifest, or return None."""
    raise NotImplementedError


def read_batches(store: CampaignObjectStore, manifest: dict[str, Any]) -> list[pd.DataFrame]:
    """Download every manifest batch in part order, verifying each SHA-256."""
    raise NotImplementedError


def labeled_ids(store: CampaignObjectStore, manifest: dict[str, Any]) -> set[str]:
    raise NotImplementedError


def consolidate_final(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    manifest: dict[str, Any],
    manifest_etag: str,
    *,
    expected_ids: Sequence[str],
    spec: FeatureSpec,
    run_id: str,
) -> str | None:
    """Write ``final.parquet`` once every expected id has exactly one row; return the new manifest ETag or None."""
    raise NotImplementedError
