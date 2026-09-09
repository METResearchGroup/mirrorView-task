"""Pinned constants for remaining labels on the 10,000 row catalog."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from shared.data.registry import (
    STUDY_PHASE_2_PART_2_RESULTS_FULL,
    STUDY_PHASE_2_PART_2_STIMULI,
)

REQUIRED_LABELS_PER_POST = 5
OLD_STIMULI_DATASET = STUDY_PHASE_2_PART_2_STIMULI
OLD_RESULTS_DATASET = STUDY_PHASE_2_PART_2_RESULTS_FULL
EXPECTED_OLD_CATALOG_IDS = 10000
OLD_ID_COLUMN = "post_primary_key"
RESULTS_ID_COLUMN = "post_id"
RATER_COLUMN = "prolific_id"
NEW_ID_COLUMN = "post_primary_key"
OUTPUT_ID_COLUMN = "id"
OUTPUT_COUNT_COLUMN = "number_of_times_to_label"
OUTPUT_BATCH_COLUMN = "batch"
OUTPUT_COLUMNS = (OUTPUT_ID_COLUMN, OUTPUT_COUNT_COLUMN, OUTPUT_BATCH_COLUMN)
EMPTY_CELL = ""
NAN_CELL = "nan"
SORT_KIND = "mergesort"
CSV_INDEX = False

NEW_CATALOG_S3_BUCKET = "mirrorview-experimental-artifacts"
NEW_CATALOG_S3_KEY = "experiments/curate_study_2_phase_3_stimuli/flips.csv"
NEW_CATALOG_S3_URI = f"s3://{NEW_CATALOG_S3_BUCKET}/{NEW_CATALOG_S3_KEY}"
NEW_CATALOG_SHA256 = (
    "c90fdcf86e89e393f0de4cc34e1dc4e4bb2bd876405926ad654ff679f3ab4139"
)
NEW_CATALOG_ROW_COUNT = 10000

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    "experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/"
    "required_label_count_per_stimulus_post.csv"
)
DATASET_FILENAME = "required_label_count_per_stimulus_post.csv"
RESULTS_FILENAME = "RESULTS.md"
CACHE_DIRNAME = "cache"
CACHE_FILENAME = "flips.csv"
EXPERIMENT_DIRNAME = "calculate_v2_required_label_count_per_stimulus_post_2026_09_08"


class Batch(str, Enum):
    """Which stimulus batch a remaining-label row belongs to."""

    OLD = "old"
    NEW = "new"


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


PINNED_NEW_CATALOG = NewCatalogSource(
    s3_uri=NEW_CATALOG_S3_URI,
    sha256=NEW_CATALOG_SHA256,
    expected_row_count=NEW_CATALOG_ROW_COUNT,
)


def pinned_new_catalog() -> NewCatalogSource:
    """Return the pinned 10,000 row catalog identity."""
    return PINNED_NEW_CATALOG
