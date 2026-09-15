"""Pinned counts and paths for the mixed-feed overprovisioned CSV.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_PREFIX,
    DEMOCRAT_LEFT_ONLY_COUNT,
    DEMOCRAT_ROW_COUNT as ORIGINAL_DEMOCRAT_ROW_COUNT,
    EXPECTED_LEFT_ONLY,
    EXPECTED_SOURCE_ROWS,
    EXPECTED_TEN_TEN,
    EXPERIMENTAL_S3_BUCKET,
    PINNED_ASSIGNMENTS_S3_URI,
    PINNED_ASSIGNMENTS_SHA256,
    REPUBLICAN_LEFT_ONLY_COUNT,
    REPUBLICAN_ROW_COUNT as ORIGINAL_REPUBLICAN_ROW_COUNT,
    STUDY_BUCKET,
    STUDY_NAME,
    USER_ID_WIDTH,
)

CLONE_COUNT = 1000
SAMPLE_SEED = 0
BASE_USER_COUNT = EXPECTED_SOURCE_ROWS
MIXED_SOURCE_COUNT = EXPECTED_TEN_TEN
LEFTOVER_LEFT_COUNT = EXPECTED_LEFT_ONLY
EXTRA_FIRST_USER_ID = 3880
TOTAL_USER_COUNT = 4879
DEMOCRAT_ROW_COUNT = 2440
REPUBLICAN_ROW_COUNT = 2439
DEMOCRAT_LEFTOVER_LEFT_COUNT = DEMOCRAT_LEFT_ONLY_COUNT
REPUBLICAN_LEFTOVER_LEFT_COUNT = REPUBLICAN_LEFT_ONLY_COUNT
DEMOCRAT_MIXED_COUNT = 2101
REPUBLICAN_MIXED_COUNT = 2101
EXTRA_DEMOCRAT_COUNT = 500
EXTRA_REPUBLICAN_COUNT = 500
POSTS_PER_FEED = 20
ASSIGNMENT_SLOTS = TOTAL_USER_COUNT * POSTS_PER_FEED
MINIMUM_CLONE_COUNT = 1
SAMPLE_WITH_REPLACEMENT = False
EXPERIMENT_DIRNAME = "upsample_mixed_study_feeds_2026_09_11"
BATCH_DIRNAME = "batch"
CACHE_DIRNAME = "cache"
OVERPROVISIONED_FILENAME = "study_user_assignments_overprovisioned.csv"
ASSIGNMENTS_OVERPROVISIONED_FILENAME = "assignments_overprovisioned.csv"
CATALOG_FILENAME = "catalog.csv"
CONFIG_FILENAME = "config.yaml"
RESULTS_FILENAME = "RESULTS.md"
OVERPROVISIONED_S3_KEY = (
    f"experiments/{EXPERIMENT_DIRNAME}/{OVERPROVISIONED_FILENAME}"
)
OVERPROVISIONED_S3_URI = (
    f"s3://{EXPERIMENTAL_S3_BUCKET}/{OVERPROVISIONED_S3_KEY}"
)
PINNED_SOURCE_ASSIGNMENTS_S3_URI = PINNED_ASSIGNMENTS_S3_URI
PINNED_SOURCE_ASSIGNMENTS_SHA256 = PINNED_ASSIGNMENTS_SHA256
STUDY_S3_BUCKET = STUDY_BUCKET
STUDY_ASSIGNMENT_PREFIX = ASSIGNMENT_PREFIX
STUDY_CONFIG_NAME = STUDY_NAME
ORIGINAL_DEMOCRAT_COUNT = ORIGINAL_DEMOCRAT_ROW_COUNT
ORIGINAL_REPUBLICAN_COUNT = ORIGINAL_REPUBLICAN_ROW_COUNT
USER_ID_DIGIT_WIDTH = USER_ID_WIDTH
FIRST_EXTRA_DEMOCRAT_INDEX = 1941
FIRST_EXTRA_REPUBLICAN_INDEX = 1940
LIVE_BATCH_TIMESTAMP = "2026_09_09-23:06:02"
LIVE_S3_PREFIX = f"{STUDY_ASSIGNMENT_PREFIX}/{LIVE_BATCH_TIMESTAMP}"
ASSIGNMENTS_ORIGINAL_FILENAME = "assignments_original.csv"
CONFIG_ORIGINAL_FILENAME = "config_original.yaml"
PRE_CUTOVER_CONFIG_SHA256 = (
    "948a23b557349a6125ee8f4a3ff998b8bfacb55a0182880c4e8ec3bb8ec041ad"
)
PRE_CUTOVER_DEMOCRAT_CSV_SHA256 = (
    "73c8e74883c1eb45f996a9a05801b4c5cb43e4115670ab5bf9d645d46b66b648"
)
PRE_CUTOVER_REPUBLICAN_CSV_SHA256 = (
    "f4ef1cf51734e1ae4929047586cc9ec75904a9134693e43c6563507671858b99"
)
DYNAMODB_REGION = "us-east-2"
STUDY_ASSIGNMENT_COUNTER_TABLE = "study_assignment_counter"
USER_ASSIGNMENTS_TABLE = "user_assignments"
STUDY_ID = "mirrorview"
DEMOCRAT_ITERATION_ASSIGNMENT_KEY = (
    f"{STUDY_CONFIG_NAME}#democrat:training_assisted"
)
REPUBLICAN_ITERATION_ASSIGNMENT_KEY = (
    f"{STUDY_CONFIG_NAME}#republican:training_assisted"
)
DEMOCRAT_MANUAL_TEST_ITERATION_USER_KEY = (
    f"{STUDY_CONFIG_NAME}#manual-test-2026-09-09-d"
)
REPUBLICAN_MANUAL_TEST_ITERATION_USER_KEY = (
    f"{STUDY_CONFIG_NAME}#manual-test-2026-09-09-r"
)
DEMOCRAT_FIRST_ASSIGNMENT_ID = "democrat-training_assisted-0001"
REPUBLICAN_FIRST_ASSIGNMENT_ID = "republican-training_assisted-0001"
DEMOCRAT_FIRST_EXTRA_ASSIGNMENT_ID = "democrat-training_assisted-1941"
DEMOCRAT_LAST_ASSIGNMENT_ID = "democrat-training_assisted-2440"
REPUBLICAN_FIRST_EXTRA_ASSIGNMENT_ID = "republican-training_assisted-1940"
REPUBLICAN_LAST_ASSIGNMENT_ID = "republican-training_assisted-2439"
CUTOVER_VERIFY_LOG_PATH = "/opt/cursor/artifacts/cutover_verify.log"


@dataclass(frozen=True)
class UpsampleCounts:
    """Row counts produced by one upsample run."""

    base_users: int
    mixed_source: int
    cloned_feeds: int
    total_user_count: int
    extra_democrat_count: int
    extra_republican_count: int


@dataclass(frozen=True)
class UpsampleRunResult:
    """Counts and paths from one overprovisioned CSV run."""

    counts: UpsampleCounts
    democrat_rows: int
    republican_rows: int
    assignment_slots: int
    local_path: str
    experimental_s3_uri: str
    csv_sha256: str


def experiment_dir(repo_root: Path) -> Path:
    """Return the experiment folder under ``repo_root``."""
    return repo_root / "experiments" / EXPERIMENT_DIRNAME
