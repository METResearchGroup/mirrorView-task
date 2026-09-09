"""Pinned combined parquet, 10,200 sample, and upsample output constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CANDIDATE_COLUMNS,
    CANDIDATE_S3_URI,
    CANDIDATE_SHA256,
    CANDIDATE_SORT_COLUMNS,
    CandidateSource,
)
from lib.constants import REPO_ROOT

COMBINED_ROW_COUNT = 55573
SAMPLE_S3_BUCKET = "mirrorview-experimental-artifacts"
SAMPLE_S3_KEY = (
    "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"
)
SAMPLE_S3_URI = f"s3://{SAMPLE_S3_BUCKET}/{SAMPLE_S3_KEY}"
SAMPLE_SHA256 = "9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9"
SAMPLE_ROW_COUNT = 10200

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/"
    "upsample_2000_medium_toxicity_posts.parquet"
)
OUTPUT_S3_URI = f"s3://{OUTPUT_S3_BUCKET}/{OUTPUT_S3_KEY}"
DATASET_FILENAME = "upsample_2000_medium_toxicity_posts.parquet"
RESULTS_FILENAME = "RESULTS.md"
EXPERIMENT_DIRNAME = "upsample_medium_toxicity_posts_2026_09_08"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
COMBINED_CACHE_DIRNAME = "combined"
SAMPLE_CACHE_DIRNAME = "sample"
CACHE_DIR = EXPERIMENT_DIR / "cache"

OUTPUT_COLUMNS = CANDIDATE_COLUMNS
SORT_COLUMNS = CANDIDATE_SORT_COLUMNS
RECORD_ID_COLUMN = "record_id"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
LEFT_STANCE = "left"
RIGHT_STANCE = "right"
MEDIUM_TOXICITY = "medium"
SAMPLE_SEED = 42
TARGET_PER_STANCE = 1000
TARGET_TOTAL = 2000
SORT_KIND = "mergesort"
EXPECTED_LEFTOVER_LEFT_MEDIUM = 15203
EXPECTED_LEFTOVER_RIGHT_MEDIUM = 3865


@dataclass(frozen=True)
class LeftoverMediumSample:
    """Sampled leftover medium rows plus leftover cell counts before sampling."""

    sampled: pd.DataFrame
    leftover_left_medium: int
    leftover_right_medium: int


@dataclass(frozen=True)
class UpsampleRunResult:
    """Counts and paths from one unused medium upsample run."""

    sampled_rows: int
    left_medium: int
    right_medium: int
    leftover_left_medium: int
    leftover_right_medium: int
    local_path: str
    s3_uri: str
    dataset_sha256: str


PINNED_COMBINED = CandidateSource(
    s3_uri=CANDIDATE_S3_URI,
    sha256=CANDIDATE_SHA256,
    expected_row_count=COMBINED_ROW_COUNT,
)

PINNED_SAMPLE = CandidateSource(
    s3_uri=SAMPLE_S3_URI,
    sha256=SAMPLE_SHA256,
    expected_row_count=SAMPLE_ROW_COUNT,
)


def pinned_combined_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    return PINNED_COMBINED


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    return PINNED_SAMPLE


def combined_cache_dir() -> Path:
    """Return the local cache folder for the combined parquet."""
    return CACHE_DIR / COMBINED_CACHE_DIRNAME


def sample_cache_dir() -> Path:
    """Return the local cache folder for the 10,200 post sample."""
    return CACHE_DIR / SAMPLE_CACHE_DIRNAME
