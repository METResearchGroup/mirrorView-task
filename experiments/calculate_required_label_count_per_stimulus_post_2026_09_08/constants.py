"""Pinned constants for remaining labels per stimulus post.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

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
NEW_ID_COLUMN = "record_id"
OUTPUT_ID_COLUMN = "id"
OUTPUT_COUNT_COLUMN = "number_of_times_to_label"
OUTPUT_BATCH_COLUMN = "batch"
OUTPUT_COLUMNS = (OUTPUT_ID_COLUMN, OUTPUT_COUNT_COLUMN, OUTPUT_BATCH_COLUMN)
EMPTY_CELL = ""
NAN_CELL = "nan"
SORT_KIND = "mergesort"
CSV_INDEX = False

NEW_SAMPLE_S3_BUCKET = "mirrorview-experimental-artifacts"
NEW_SAMPLE_S3_KEY = (
    "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"
)
NEW_SAMPLE_S3_URI = f"s3://{NEW_SAMPLE_S3_BUCKET}/{NEW_SAMPLE_S3_KEY}"
NEW_SAMPLE_SHA256 = "9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9"
NEW_SAMPLE_ROW_COUNT = 10200

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    "experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/"
    "required_label_count_per_stimulus_post.csv"
)
DATASET_FILENAME = "required_label_count_per_stimulus_post.csv"
RESULTS_FILENAME = "RESULTS.md"
CACHE_DIRNAME = "cache"
EXPERIMENT_DIRNAME = "calculate_required_label_count_per_stimulus_post_2026_09_08"


class Batch(str, Enum):
    """Which stimulus batch a remaining-label row belongs to."""

    OLD = "old"
    NEW = "new"


@dataclass(frozen=True)
class NewSampleSource:
    """Pinned new sample parquet identity."""

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
    new_sample_uri: str
    new_sample_sha256: str
    new_sample_rows: int


@dataclass(frozen=True)
class LocalCsvWrite:
    """Local CSV path and file bytes."""

    path: Path
    body: bytes


PINNED_NEW_SAMPLE = NewSampleSource(
    s3_uri=NEW_SAMPLE_S3_URI,
    sha256=NEW_SAMPLE_SHA256,
    expected_row_count=NEW_SAMPLE_ROW_COUNT,
)


def pinned_new_sample() -> NewSampleSource:
    """Return the pinned new sample identity."""
    return PINNED_NEW_SAMPLE
