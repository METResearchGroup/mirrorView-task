"""Pinned constants for converting the pull request 278 assignment CSV.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    NEW_CATALOG_S3_BUCKET,
    NEW_CATALOG_SHA256,
    NEW_CATALOG_S3_URI,
)
from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI

PINNED_ASSIGNMENTS_S3_URI = (
    "s3://mirrorview-experimental-artifacts/"
    "experiments/generate_study_user_assignments_2026_09_08/"
    "study_user_assignments.csv"
)
PINNED_ASSIGNMENTS_SHA256 = (
    "e42f4dffbe55bed2c9d2c4dae6829de7508ffefef6564d095b3458d9599752ce"
)
EXPECTED_SOURCE_ROWS = 3879
EXPECTED_TEN_TEN = 3202
EXPECTED_LEFT_ONLY = 677
DEMOCRAT_ROW_COUNT = 1940
REPUBLICAN_ROW_COUNT = 1939
DEMOCRAT_LEFT_ONLY_COUNT = 339
REPUBLICAN_LEFT_ONLY_COUNT = 338
DEMOCRAT_TEN_TEN_COUNT = 1601
REPUBLICAN_TEN_TEN_COUNT = 1601
FIRST_LEFT_ONLY_USER_ID = 3203
CONDITION = "training_assisted"
PARTY_DEMOCRAT = "democrat"
PARTY_REPUBLICAN = "republican"
STUDY_BUCKET = "jspsych-mirror-view-2026-09-09"
ASSIGNMENT_PREFIX = "precomputed_assignments"
POSTS_PER_FEED = 20
USER_ID_PREFIX = "user-"
USER_ID_WIDTH = 4
ASSIGNMENT_INDEX_WIDTH = 4
FIRST_ASSIGNMENT_INDEX = 1
ODD_REMAINDER = 1
POST_ID_COLUMN = "post_primary_key"
ORIGINAL_TEXT_COLUMN = "original_text"
TOXICITY_COLUMN = "sample_toxicity_type"
STANCE_COLUMN = "sampled_stance"
MIRROR_TEXT_COLUMN = "mirrored_text"
CATALOG_COLUMNS = (
    POST_ID_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    TOXICITY_COLUMN,
    STANCE_COLUMN,
    MIRROR_TEXT_COLUMN,
)
ASSIGNMENT_ID_COLUMN = "id"
ASSIGNED_POST_IDS_COLUMN = "assigned_post_ids"
POLITICAL_PARTY_COLUMN = "political_party"
CONDITION_COLUMN = "condition"
CREATED_AT_COLUMN = "created_at"
ASSIGNMENT_COLUMNS = (
    ASSIGNMENT_ID_COLUMN,
    ASSIGNED_POST_IDS_COLUMN,
    POLITICAL_PARTY_COLUMN,
    CONDITION_COLUMN,
    CREATED_AT_COLUMN,
)
STANCE_LEFT = "left"
STANCE_RIGHT = "right"
LEFT_POSTS_IN_TEN_TEN = 10
RIGHT_POSTS_IN_TEN_TEN = 10
LEFT_POSTS_IN_LEFT_ONLY = 20
RIGHT_POSTS_IN_LEFT_ONLY = 0
EMPTY_CELL = ""
NAN_CELL = "nan"
CSV_INDEX = False
CSV_ENCODING = "utf-8"
OLD_STIMULI_DATASET = STUDY_PHASE_2_PART_2_STIMULI
EXPERIMENTAL_S3_BUCKET = NEW_CATALOG_S3_BUCKET
PINNED_NEW_CATALOG_S3_URI = NEW_CATALOG_S3_URI
PINNED_NEW_CATALOG_SHA256 = NEW_CATALOG_SHA256
EXPERIMENT_DIRNAME = "load_study_assignments_2026_09_09"
BATCH_DIRNAME = "batch"
CACHE_DIRNAME = "cache"
CACHE_FILENAME = "study_user_assignments.csv"
ASSIGNMENTS_FILENAME = "assignments.csv"
CATALOG_FILENAME = "catalog.csv"
CONFIG_FILENAME = "config.yaml"
VERIFICATION_FILENAME = "verification_dataset.json"
STUDY_NAME = "mirrorview_2026_09_09"
EMPTY_POLITICAL_PARTY = ""


class FeedKind(str, Enum):
    """Party mix of one 20-post feed."""

    TEN_TEN = "ten_ten"
    LEFT_ONLY = "left_only"


@dataclass(frozen=True)
class AssignmentRow:
    """One assignment CSV row."""

    id: str
    assigned_post_ids: str
    political_party: str
    condition: str
    created_at: str


@dataclass(frozen=True)
class LocalFileWrite:
    """Local path and file bytes."""

    path: Path
    body: bytes


@dataclass(frozen=True)
class LoadRunResult:
    """Counts and paths from one conversion run."""

    democrat_rows: int
    republican_rows: int
    catalog_rows: int
    local_path: str
    catalog_sha256: str


def format_assignment_id(party: str, index: int) -> str:
    """Return ``{party}-training_assisted-{index:04d}``."""
    return f"{party}-{CONDITION}-{index:0{ASSIGNMENT_INDEX_WIDTH}d}"


def leftover_left_user_ids() -> set[int]:
    """Return original user ids 3203 through 3879."""
    return set(range(FIRST_LEFT_ONLY_USER_ID, EXPECTED_SOURCE_ROWS + 1))
