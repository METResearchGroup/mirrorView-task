"""Pinned sources and output constants for the right-high upsample."""

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
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    COMBINED_ROW_COUNT,
    OUTPUT_S3_URI as MEDIUM_UPSAMPLE_S3_URI,
    SAMPLE_ROW_COUNT,
    SAMPLE_S3_URI,
    SAMPLE_SHA256,
)
from lib.constants import REPO_ROOT

MEDIUM_UPSAMPLE_SHA256 = (
    "54a3fe28e5570a19cdcbf1ec33bb910d27decb98902339b3d0fa75e775f113d6"
)
MEDIUM_UPSAMPLE_ROW_COUNT = 2000

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
PROMOTED_S3_KEY = (
    "experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/"
    "upsample_300_right_high_toxicity_posts.parquet"
)
UNIFIED_S3_KEY = (
    "experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/"
    "unified_upsampled_posts.parquet"
)
PROMOTED_FILENAME = "upsample_300_right_high_toxicity_posts.parquet"
UNIFIED_FILENAME = "unified_upsampled_posts.parquet"
RESULTS_FILENAME = "RESULTS.md"
PROMOTION_IDS_FILENAME = "promotion_record_ids.json"
SCORES_FILENAME = "perspective_scores.parquet"
EXPERIMENT_DIRNAME = "upsample_right_leaning_high_toxicity_posts_2026_09_08"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
CACHE_DIR = EXPERIMENT_DIR / "cache"
COMBINED_CACHE_DIRNAME = "combined"
SAMPLE_CACHE_DIRNAME = "sample"
MEDIUM_UPSAMPLE_CACHE_DIRNAME = "medium_upsample"
OUTPUTS_DIRNAME = "outputs"
JSON_INDENT = 2

PR260_PROMOTION_IDS_PATH = (
    REPO_ROOT
    / "experiments"
    / "reddit_curated_perspective_v2_2026_09_08"
    / "outputs"
    / "promotion_source_record_ids.json"
)

OUTPUT_COLUMNS = CANDIDATE_COLUMNS
SORT_COLUMNS = CANDIDATE_SORT_COLUMNS
RECORD_ID_COLUMN = "record_id"
SOURCE_RECORD_ID_COLUMN = "source_record_id"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
TEXT_COLUMN = "text"
LEFT_STANCE = "left"
RIGHT_STANCE = "right"
MEDIUM_TOXICITY = "medium"
HIGH_TOXICITY = "high"
TOXICITY_PROB_COLUMN = "toxicity_prob"
SAMPLE_SEED = 42
SORT_KIND = "mergesort"
PROMOTION_COUNT = 300
UNIFIED_ROW_COUNT = 2300
MIN_CANDIDATES = 300
EXPECTED_LEFTOVER_RIGHT_MEDIUM_AFTER_UPSAMPLE = 2865
SCORE_FEATURE_NAME = "is_toxic_tiered"
SCORE_BATCH_SIZE = 64
SCORE_MAX_CONCURRENCY = 80
TOXICITY_PROB_MIN = 0.0
TOXICITY_PROB_MAX = 1.0
MISSING_ID_SAMPLE_SIZE = 5
ENGINE_SOURCE_RECORD_ID_COLUMN = "source_record_id"


@dataclass(frozen=True)
class CandidateBuildResult:
    """Right-medium leftover candidates and drop counts."""

    rows: pd.DataFrame
    leftover_right_medium_after_upsample: int
    pr260_ids_dropped: int


@dataclass(frozen=True)
class PromotionResult:
    """Promoted right-high rows and the unified upsample table."""

    promotion_ids: list[str]
    promoted: pd.DataFrame
    unified: pd.DataFrame


@dataclass(frozen=True)
class UnifiedUpsampleRunResult:
    """Counts and paths from one unified upsample run."""

    candidate_rows: int
    leftover_right_medium_after_upsample: int
    pr260_ids_dropped: int
    promotions: int
    unified_rows: int
    unified_medium: int
    unified_high: int
    unified_left: int
    unified_right: int
    promoted_local_path: str
    promoted_s3_uri: str
    promoted_sha256: str
    unified_local_path: str
    unified_s3_uri: str
    unified_sha256: str


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

PINNED_MEDIUM_UPSAMPLE = CandidateSource(
    s3_uri=MEDIUM_UPSAMPLE_S3_URI,
    sha256=MEDIUM_UPSAMPLE_SHA256,
    expected_row_count=MEDIUM_UPSAMPLE_ROW_COUNT,
)


def pinned_combined_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    return PINNED_COMBINED


def pinned_sample_source() -> CandidateSource:
    """Return the pinned 10,200 post sample identity."""
    return PINNED_SAMPLE


def pinned_medium_upsample_source() -> CandidateSource:
    """Return the pinned 2,000 unused medium parquet identity."""
    return PINNED_MEDIUM_UPSAMPLE


def combined_cache_dir() -> Path:
    """Return the local cache folder for the combined parquet."""
    return CACHE_DIR / COMBINED_CACHE_DIRNAME


def sample_cache_dir() -> Path:
    """Return the local cache folder for the 10,200 post sample."""
    return CACHE_DIR / SAMPLE_CACHE_DIRNAME


def medium_upsample_cache_dir() -> Path:
    """Return the local cache folder for the 2,000 medium upsample."""
    return CACHE_DIR / MEDIUM_UPSAMPLE_CACHE_DIRNAME


def scores_path() -> Path:
    """Return the local Perspective scores parquet path."""
    return EXPERIMENT_DIR / OUTPUTS_DIRNAME / SCORES_FILENAME


def promotion_ids_path() -> Path:
    """Return the committed promotion id JSON path."""
    return EXPERIMENT_DIR / OUTPUTS_DIRNAME / PROMOTION_IDS_FILENAME
