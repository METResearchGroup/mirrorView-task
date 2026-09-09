"""Pinned sources and catalog constants for the 10,000 post catalog."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CandidateSource,
)
from experiments.generate_flips_for_upsampled_posts_2026_09_08.sources import (
    INPUT_ROW_COUNT as UNIFIED_POST_ROW_COUNT,
    INPUT_S3_URI as UNIFIED_POST_S3_URI,
    INPUT_SHA256 as UNIFIED_POST_SHA256,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    SAMPLE_ROW_COUNT,
    SAMPLE_S3_URI,
    SAMPLE_SHA256,
)
from lib.constants import REPO_ROOT

SAMPLE_FLIPS_S3_BUCKET = "mirrorview-experimental-artifacts"
SAMPLE_FLIPS_S3_KEY = (
    "experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet"
)
SAMPLE_FLIPS_S3_URI = f"s3://{SAMPLE_FLIPS_S3_BUCKET}/{SAMPLE_FLIPS_S3_KEY}"
SAMPLE_FLIPS_SHA256 = (
    "f3b791f226f8f69d3ddaf0737aab0a3aaf20ebb36d45a6d9b42dec8d1e148702"
)
SAMPLE_FLIPS_ROW_COUNT = 10182

UNIFIED_FLIPS_S3_BUCKET = "mirrorview-experimental-artifacts"
UNIFIED_FLIPS_S3_KEY = (
    "experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet"
)
UNIFIED_FLIPS_S3_URI = f"s3://{UNIFIED_FLIPS_S3_BUCKET}/{UNIFIED_FLIPS_S3_KEY}"
UNIFIED_FLIPS_SHA256 = (
    "67d43ccec1725670306c2fe15f52101cee7dc21f273448dd3f9221562d168120"
)
UNIFIED_FLIPS_ROW_COUNT = 2295

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = "experiments/curate_study_2_phase_3_stimuli/flips.csv"
DATASET_FILENAME = "flips.csv"
RESULTS_FILENAME = "RESULTS.md"
EXPERIMENT_DIRNAME = "curate_study_2_phase_3_stimuli"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
CACHE_DIR = EXPERIMENT_DIR / "cache"
SAMPLE_POSTS_CACHE_DIRNAME = "sample_posts"
UNIFIED_POSTS_CACHE_DIRNAME = "unified_posts"
SAMPLE_FLIPS_CACHE_DIRNAME = "sample_flips"
UNIFIED_FLIPS_CACHE_DIRNAME = "unified_flips"
FLIPS_CACHE_FILENAME = "flips.parquet"

RECORD_ID_COLUMN = "record_id"
TEXT_COLUMN = "text"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
ORIGINAL_TEXT_COLUMN = "original_text"
MIRRORED_TEXT_COLUMN = "mirrored_text"
POST_PRIMARY_KEY_COLUMN = "post_primary_key"
SAMPLE_TOXICITY_TYPE_COLUMN = "sample_toxicity_type"
SAMPLED_STANCE_COLUMN = "sampled_stance"
CATALOG_COLUMNS = (
    POST_PRIMARY_KEY_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    SAMPLED_STANCE_COLUMN,
    MIRRORED_TEXT_COLUMN,
)
FLIP_KEEP_COLUMNS = (RECORD_ID_COLUMN, ORIGINAL_TEXT_COLUMN, MIRRORED_TEXT_COLUMN)
LEFT_STANCE = "left"
RIGHT_STANCE = "right"
LOW_TOXICITY = "low"
MEDIUM_TOXICITY = "medium"
HIGH_TOXICITY = "high"
TOXICITY_TIERS = (LOW_TOXICITY, MEDIUM_TOXICITY, HIGH_TOXICITY)
STANCE_VALUES = (LEFT_STANCE, RIGHT_STANCE)
TOXICITY_LABELS = {
    LOW_TOXICITY: "sample_low_toxicity",
    MEDIUM_TOXICITY: "sample_middle_toxicity",
    HIGH_TOXICITY: "sample_high_toxicity",
}
CELL_TARGET = {
    LEFT_STANCE: {LOW_TOXICITY: 1250, MEDIUM_TOXICITY: 2500, HIGH_TOXICITY: 1250},
    RIGHT_STANCE: {LOW_TOXICITY: 1250, MEDIUM_TOXICITY: 2500, HIGH_TOXICITY: 1250},
}
SAMPLE_SEED = 42
SORT_KIND = "mergesort"
CATALOG_TOTAL = 10000
CSV_INDEX = False
CSV_ENCODING = "utf-8"
EMPTY_CELL = ""


@dataclass(frozen=True)
class FlipSource:
    """One pinned flips parquet."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class JoinedFlipPool:
    """Posts that have a successful flip, from the sample and the upsample."""

    rows: pd.DataFrame
    sample_joined_rows: int
    upsample_joined_rows: int


@dataclass(frozen=True)
class CatalogRunResult:
    """Counts and paths from one catalog run, including a pause."""

    available: dict[str, dict[str, int]]
    catalog_written: bool
    catalog_rows: int
    local_path: str
    s3_uri: str
    csv_sha256: str


PINNED_SAMPLE = CandidateSource(
    s3_uri=SAMPLE_S3_URI,
    sha256=SAMPLE_SHA256,
    expected_row_count=SAMPLE_ROW_COUNT,
)

PINNED_UNIFIED = CandidateSource(
    s3_uri=UNIFIED_POST_S3_URI,
    sha256=UNIFIED_POST_SHA256,
    expected_row_count=UNIFIED_POST_ROW_COUNT,
)

PINNED_SAMPLE_FLIPS = FlipSource(
    s3_uri=SAMPLE_FLIPS_S3_URI,
    sha256=SAMPLE_FLIPS_SHA256,
    expected_row_count=SAMPLE_FLIPS_ROW_COUNT,
)

PINNED_UNIFIED_FLIPS = FlipSource(
    s3_uri=UNIFIED_FLIPS_S3_URI,
    sha256=UNIFIED_FLIPS_SHA256,
    expected_row_count=UNIFIED_FLIPS_ROW_COUNT,
)


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    return PINNED_SAMPLE


def pinned_unified_source() -> CandidateSource:
    """Return the pinned unified 2,300 post parquet identity."""
    return PINNED_UNIFIED


def pinned_sample_flips() -> FlipSource:
    """Return the pinned existing sample flips identity."""
    return PINNED_SAMPLE_FLIPS


def pinned_unified_flips() -> FlipSource:
    """Return the pinned unified upsample flips identity."""
    return PINNED_UNIFIED_FLIPS


def sample_posts_cache_dir() -> Path:
    """Return the cache folder for the 10,200 post sample."""
    return CACHE_DIR / SAMPLE_POSTS_CACHE_DIRNAME


def unified_posts_cache_dir() -> Path:
    """Return the cache folder for the unified 2,300 posts."""
    return CACHE_DIR / UNIFIED_POSTS_CACHE_DIRNAME


def sample_flips_cache_dir() -> Path:
    """Return the cache folder for the existing sample flips."""
    return CACHE_DIR / SAMPLE_FLIPS_CACHE_DIRNAME


def unified_flips_cache_dir() -> Path:
    """Return the cache folder for the unified upsample flips."""
    return CACHE_DIR / UNIFIED_FLIPS_CACHE_DIRNAME
