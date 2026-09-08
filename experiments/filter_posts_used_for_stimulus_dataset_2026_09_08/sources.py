"""Pinned candidate parquet and sample constants for the filter run."""

from __future__ import annotations

from dataclasses import dataclass

from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_COLUMNS,
    SORT_COLUMNS,
    STANCE_CROSSTAB_ROWS,
    TOXICITY_CROSSTAB_COLUMNS,
)

CANDIDATE_COLUMNS = COMBINED_COLUMNS
CANDIDATE_SORT_COLUMNS = SORT_COLUMNS
CANDIDATE_STANCE_ROWS = STANCE_CROSSTAB_ROWS
CANDIDATE_TOXICITY_COLUMNS = TOXICITY_CROSSTAB_COLUMNS
CANDIDATE_S3_BUCKET = "mirrorview-experimental-artifacts"
CANDIDATE_S3_KEY = "experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet"
CANDIDATE_S3_URI = f"s3://{CANDIDATE_S3_BUCKET}/{CANDIDATE_S3_KEY}"
CANDIDATE_SHA256 = "f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0"
CANDIDATE_ROW_COUNT = 55573

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"
)
OUTPUT_S3_URI = f"s3://{OUTPUT_S3_BUCKET}/{OUTPUT_S3_KEY}"
DATASET_FILENAME = "dataset.parquet"
RESULTS_FILENAME = "RESULTS.md"
TARGET_PER_CELL = 1700
TARGET_TOTAL = 10200
SAMPLE_SEED = 42
RECORD_ID_COLUMN = "record_id"
TEXT_COLUMN = "text"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
RIGHT_STANCE = "right"
HIGH_TOXICITY = "high"


@dataclass(frozen=True)
class CandidateSource:
    """One pinned combined parquet used as the filter input."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class CleanupSummary:
    """Row counts after each cleanup step."""

    candidate_rows: int
    dropped_previous_ids: int
    dropped_previous_text: int
    dropped_duplicate_ids: int
    dropped_duplicate_text: int
    cleaned_rows: int


@dataclass(frozen=True)
class FilterRunResult:
    """Local path, S3 URI, hash, and counts from one filter run."""

    candidate_rows: int
    cleaned_rows: int
    sampled_rows: int
    right_high_available: int
    right_high_shortfall: int
    local_path: str
    s3_uri: str
    dataset_sha256: str
    cleanup_summary: CleanupSummary
    cleaned_crosstab: dict[str, dict[str, int]]
    sampled_crosstab: dict[str, dict[str, int]]
    sampled_integration_crosstab: dict[str, dict[str, dict[str, int]]]


PINNED_CANDIDATE = CandidateSource(
    s3_uri=CANDIDATE_S3_URI,
    sha256=CANDIDATE_SHA256,
    expected_row_count=CANDIDATE_ROW_COUNT,
)


def pinned_candidate_source() -> CandidateSource:
    """Return the pinned combined parquet identity."""
    raise NotImplementedError
