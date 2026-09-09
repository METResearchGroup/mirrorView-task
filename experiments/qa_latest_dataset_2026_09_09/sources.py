"""Pinned flips parquet for QA of the latest stimulus sample."""

from __future__ import annotations

from dataclasses import dataclass

from shared.flip_generation.models import FLIP_PARQUET_COLUMNS

INPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
INPUT_S3_KEY = (
    "experiments/generate_flips_2026_09_08/2026_09_08-20:31:31/flips.parquet"
)
INPUT_SHA256 = "f3b791f226f8f69d3ddaf0737aab0a3aaf20ebb36d45a6d9b42dec8d1e148702"
INPUT_ROW_COUNT = 10182
INPUT_S3_URI = f"s3://{INPUT_S3_BUCKET}/{INPUT_S3_KEY}"
CACHE_FILENAME = "flips.parquet"
FLIP_COLUMNS = FLIP_PARQUET_COLUMNS
RECORD_ID_COLUMN = "record_id"
ORIGINAL_TEXT_COLUMN = "original_text"
MIRRORED_TEXT_COLUMN = "mirrored_text"
STANCE_COLUMN = "political_stance"
TOXICITY_COLUMN = "llm_toxicity_tier"
ID_DISPLAY_COLUMN = "ID"
ORIGINAL_TEXT_DISPLAY_COLUMN = "original text"
MIRROR_TEXT_DISPLAY_COLUMN = "mirror text"
POLITICAL_LEAN_DISPLAY_COLUMN = "political lean"
TOXICITY_TIER_DISPLAY_COLUMN = "toxicity tier"
QA_COLUMN_RENAME = {
    RECORD_ID_COLUMN: ID_DISPLAY_COLUMN,
    ORIGINAL_TEXT_COLUMN: ORIGINAL_TEXT_DISPLAY_COLUMN,
    MIRRORED_TEXT_COLUMN: MIRROR_TEXT_DISPLAY_COLUMN,
    STANCE_COLUMN: POLITICAL_LEAN_DISPLAY_COLUMN,
    TOXICITY_COLUMN: TOXICITY_TIER_DISPLAY_COLUMN,
}
QA_COLUMNS = (
    ID_DISPLAY_COLUMN,
    ORIGINAL_TEXT_DISPLAY_COLUMN,
    MIRROR_TEXT_DISPLAY_COLUMN,
    POLITICAL_LEAN_DISPLAY_COLUMN,
    TOXICITY_TIER_DISPLAY_COLUMN,
)


@dataclass(frozen=True)
class FlipsSource:
    """One pinned flips parquet used as the QA input."""

    uri: str
    sha256: str
    expected_row_count: int


PINNED_FLIPS = FlipsSource(
    uri=INPUT_S3_URI,
    sha256=INPUT_SHA256,
    expected_row_count=INPUT_ROW_COUNT,
)


def pinned_flips_source() -> FlipsSource:
    """Return the pinned flips parquet identity."""
    return PINNED_FLIPS
