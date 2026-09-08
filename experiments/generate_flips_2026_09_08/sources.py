"""Pinned filtered parquet and run constants for flip generation."""

from __future__ import annotations

from dataclasses import dataclass

INPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
INPUT_S3_KEY = "experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet"
INPUT_SHA256 = "9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9"
INPUT_ROW_COUNT = 10200
OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
RUN_KEY_PREFIX = "experiments/generate_flips_2026_09_08/"
CACHE_FILENAME = "dataset.parquet"
SMOKE_RUN_ID = "smoke"
SMOKE_MAX_POSTS = 10
POST_COLUMNS = (
    "record_id",
    "text",
    "political_stance",
    "llm_toxicity_tier",
)
INPUT_S3_URI = f"s3://{INPUT_S3_BUCKET}/{INPUT_S3_KEY}"


@dataclass(frozen=True)
class FilteredSource:
    """One pinned filtered parquet used as flip-generation input."""

    uri: str
    sha256: str
    expected_row_count: int


PINNED_FILTERED = FilteredSource(
    uri=INPUT_S3_URI,
    sha256=INPUT_SHA256,
    expected_row_count=INPUT_ROW_COUNT,
)


def pinned_filtered_source() -> FilteredSource:
    """Return the pinned filtered parquet identity."""
    return PINNED_FILTERED
