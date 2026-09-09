"""Pinned constants for remaining labels on the 10,000 row catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

REQUIRED_LABELS_PER_POST = 5


@dataclass(frozen=True)
class NewCatalogSource:
    """Pinned new catalog CSV identity."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class LabelCountRunResult:
    """Counts and paths from one remaining-label run."""

    old_catalog_ids: int
    old_posts: int
    old_labels: int
    new_posts: int
    new_labels: int
    total_posts: int
    total_labels: int
    local_path: str
    s3_uri: str
    csv_sha256: str
    new_catalog_uri: str
    new_catalog_sha256: str
    new_catalog_rows: int


@dataclass(frozen=True)
class LocalCsvWrite:
    """Local CSV path and file bytes."""

    path: Path
    body: bytes


def pinned_new_catalog() -> NewCatalogSource:
    """Return the pinned 10,000 row catalog identity."""
    raise NotImplementedError
