"""Pinned MirrorView curated parquet sources for the stimulus combine run."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Integration(str, Enum):
    """Platform that produced a curated export."""

    BLUESKY = "bluesky"
    REDDIT = "reddit"
    TWITTER = "twitter"


@dataclass(frozen=True)
class CuratedSource:
    """One pinned curated parquet object used as a combine input."""

    integration: Integration
    dataset_id: str
    curated_run: str
    s3_uri: str
    sha256: str
    expected_row_count: int
    platform_id_column: str


@dataclass(frozen=True)
class CombineRunResult:
    """Local path, S3 URI, hash, and counts from one combine run."""

    combined_rows: int
    local_path: str
    s3_uri: str
    dataset_sha256: str
    overall_crosstab: dict[str, dict[str, int]]
    integration_crosstab: dict[str, dict[str, dict[str, int]]]


BLUESKY_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
BLUESKY_CURATED_RUN = "2026_09_06-23:25:06"
BLUESKY_S3_URI = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/bluesky/"
    f"{BLUESKY_DATASET_ID}/curated/{BLUESKY_CURATED_RUN}/mirrorview.parquet"
)
BLUESKY_SHA256 = "35e3f05111a16c27b95538894cda18db6d7295c8aad6be4fb7cb83ecafb1b3bc"
BLUESKY_ROW_COUNT = 9756
BLUESKY_PLATFORM_ID_COLUMN = "uri"

TWITTER_DATASET_ID_RUN_1 = "twitter_fba4ddb2-fcf7-4a13-a7cc-0d98db44b547"
TWITTER_CURATED_RUN_1 = "2026_09_07-06:58:09"
TWITTER_S3_URI_RUN_1 = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/twitter/"
    f"{TWITTER_DATASET_ID_RUN_1}/curated/{TWITTER_CURATED_RUN_1}/mirrorview.parquet"
)
TWITTER_SHA256_RUN_1 = "7639e54554869371fdb6397a1c2a497b32711679290322b999fb68ee173f39c9"
TWITTER_ROW_COUNT_RUN_1 = 1457

TWITTER_DATASET_ID_RUN_2 = "twitter_5901767a-e609-46fc-9a17-742516b548f2"
TWITTER_CURATED_RUN_2 = "2026_09_08-05:34:19"
TWITTER_S3_URI_RUN_2 = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/twitter/"
    f"{TWITTER_DATASET_ID_RUN_2}/curated/{TWITTER_CURATED_RUN_2}/mirrorview.parquet"
)
TWITTER_SHA256_RUN_2 = "c2178c27165c26dd960bd470e3ee98791e7c98638a346eca0f0fafa1c065c8e2"
TWITTER_ROW_COUNT_RUN_2 = 1299
TWITTER_PLATFORM_ID_COLUMN = "tweet_id"

REDDIT_DATASET_ID = "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079"
REDDIT_CURATED_RUN = "2026_09_07-21:47:32"
REDDIT_S3_URI = (
    "s3://mirrorview-experimental-artifacts/data_platform/data/reddit/"
    f"{REDDIT_DATASET_ID}/curated/{REDDIT_CURATED_RUN}/mirrorview_v2.parquet"
)
REDDIT_SHA256 = "e1d9b1494fd2ef030dc8fdc1f71980b55d972e4a01da23923fa6f61a693a3936"
REDDIT_ROW_COUNT = 43061
REDDIT_PLATFORM_ID_COLUMN = "comment_fullname"

COMBINED_ROW_COUNT = 55573
COMBINED_COLUMNS = (
    "integration",
    "source_dataset_id",
    "source_curated_run",
    "record_id",
    "source_record_id",
    "platform_id",
    "author_handle",
    "text",
    "created_at",
    "sync_timestamp",
    "news_or_opinion_category",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tier",
)
SORT_COLUMNS = ("integration", "source_dataset_id", "source_record_id")
STANCE_CROSSTAB_ROWS = ("left", "right")
TOXICITY_CROSSTAB_COLUMNS = ("low", "medium", "high")
INTEGRATION_CROSSTAB_ORDER = (
    Integration.BLUESKY.value,
    Integration.REDDIT.value,
    Integration.TWITTER.value,
)

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = "experiments/combine_data_into_stimulus_set_2026_09_08/dataset.parquet"
OUTPUT_S3_URI = f"s3://{OUTPUT_S3_BUCKET}/{OUTPUT_S3_KEY}"
DATASET_FILENAME = "dataset.parquet"
RESULTS_FILENAME = "RESULTS.md"

PINNED_SOURCES = (
    CuratedSource(
        integration=Integration.BLUESKY,
        dataset_id=BLUESKY_DATASET_ID,
        curated_run=BLUESKY_CURATED_RUN,
        s3_uri=BLUESKY_S3_URI,
        sha256=BLUESKY_SHA256,
        expected_row_count=BLUESKY_ROW_COUNT,
        platform_id_column=BLUESKY_PLATFORM_ID_COLUMN,
    ),
    CuratedSource(
        integration=Integration.TWITTER,
        dataset_id=TWITTER_DATASET_ID_RUN_1,
        curated_run=TWITTER_CURATED_RUN_1,
        s3_uri=TWITTER_S3_URI_RUN_1,
        sha256=TWITTER_SHA256_RUN_1,
        expected_row_count=TWITTER_ROW_COUNT_RUN_1,
        platform_id_column=TWITTER_PLATFORM_ID_COLUMN,
    ),
    CuratedSource(
        integration=Integration.TWITTER,
        dataset_id=TWITTER_DATASET_ID_RUN_2,
        curated_run=TWITTER_CURATED_RUN_2,
        s3_uri=TWITTER_S3_URI_RUN_2,
        sha256=TWITTER_SHA256_RUN_2,
        expected_row_count=TWITTER_ROW_COUNT_RUN_2,
        platform_id_column=TWITTER_PLATFORM_ID_COLUMN,
    ),
    CuratedSource(
        integration=Integration.REDDIT,
        dataset_id=REDDIT_DATASET_ID,
        curated_run=REDDIT_CURATED_RUN,
        s3_uri=REDDIT_S3_URI,
        sha256=REDDIT_SHA256,
        expected_row_count=REDDIT_ROW_COUNT,
        platform_id_column=REDDIT_PLATFORM_ID_COLUMN,
    ),
)


def pinned_sources() -> tuple[CuratedSource, ...]:
    """Return the four pinned curated sources in combine order."""
    return PINNED_SOURCES
