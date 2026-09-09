"""Pinned unified upsample parquet and flip-run constants."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.constants import REPO_ROOT

INPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
INPUT_S3_KEY = (
    "experiments/upsample_right_leaning_high_toxicity_posts_2026_09_08/"
    "unified_upsampled_posts.parquet"
)
INPUT_SHA256 = "853ae3e2b58bf8e4629c1a83c22bde28fbfdf57b10631511625ce97b72aaa007"
INPUT_ROW_COUNT = 2300
OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
RUN_KEY_PREFIX = "experiments/generate_flips_for_upsampled_posts_2026_09_08/"
NAMED_SIBLING_S3_KEY = (
    "experiments/generate_flips_2026_09_08/flips_unified_upsampled_posts.parquet"
)
CACHE_FILENAME = "unified_upsampled_posts.parquet"
SMOKE_RUN_ID = "smoke"
SMOKE_MAX_POSTS = 10
POST_COLUMNS = (
    "record_id",
    "text",
    "political_stance",
    "llm_toxicity_tier",
)
INPUT_S3_URI = f"s3://{INPUT_S3_BUCKET}/{INPUT_S3_KEY}"
EXPERIMENT_DIRNAME = "generate_flips_for_upsampled_posts_2026_09_08"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
DEFAULT_CACHE_DIR = EXPERIMENT_DIR / "cache"
RESULTS_FILENAME = "RESULTS.md"


@dataclass(frozen=True)
class UnifiedSource:
    """One pinned unified upsample parquet used as flip-generation input."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class NamedFlipCopyResult:
    """Named sibling copy of the concatenated flips parquet."""

    s3_uri: str
    sha256: str


PINNED_UNIFIED = UnifiedSource(
    s3_uri=INPUT_S3_URI,
    sha256=INPUT_SHA256,
    expected_row_count=INPUT_ROW_COUNT,
)


def pinned_unified_source() -> UnifiedSource:
    """Return the pinned unified 2,300 post parquet identity."""
    return PINNED_UNIFIED
