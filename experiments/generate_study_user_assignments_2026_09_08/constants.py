"""Pinned constants for study user assignment generation.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from shared.data.registry import STUDY_PHASE_2_PART_2_STIMULI

POSTS_PER_FEED = 20
LEFT_POSTS_IN_TEN_TEN = 10
RIGHT_POSTS_IN_TEN_TEN = 10
LEFT_POSTS_IN_LEFT_ONLY = 20
RIGHT_POSTS_IN_LEFT_ONLY = 0
CATALOG_SHUFFLE_SEED = 0
USER_ID_START = 1
ODD_REMAINDER = 1
CELL_COUNT = 6
LEFT_CELLS = (1, 2, 3)
RIGHT_CELLS = (4, 5, 6)

OLD_STIMULI_DATASET = STUDY_PHASE_2_PART_2_STIMULI
POST_ID_COLUMN = "post_primary_key"
STANCE_COLUMN = "sampled_stance"
TOXICITY_COLUMN = "sample_toxicity_type"
REMAINING_ID_COLUMN = "id"
REMAINING_COUNT_COLUMN = "number_of_times_to_label"
REMAINING_BATCH_COLUMN = "batch"
REMAINING_COLUMNS = (
    REMAINING_ID_COLUMN,
    REMAINING_COUNT_COLUMN,
    REMAINING_BATCH_COLUMN,
)
CELL_COLUMN = "cell"
CATALOG_COLUMNS = (POST_ID_COLUMN, STANCE_COLUMN, TOXICITY_COLUMN)
SHUFFLED_COLUMNS = (
    POST_ID_COLUMN,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
    REMAINING_COUNT_COLUMN,
    CELL_COLUMN,
)
STANCE_LEFT = "left"
STANCE_RIGHT = "right"
TOXICITY_LOW = "sample_low_toxicity"
TOXICITY_MIDDLE = "sample_middle_toxicity"
TOXICITY_HIGH = "sample_high_toxicity"
CELL_BY_STANCE_TOXICITY = {
    (STANCE_LEFT, TOXICITY_LOW): 1,
    (STANCE_LEFT, TOXICITY_MIDDLE): 2,
    (STANCE_LEFT, TOXICITY_HIGH): 3,
    (STANCE_RIGHT, TOXICITY_LOW): 4,
    (STANCE_RIGHT, TOXICITY_MIDDLE): 5,
    (STANCE_RIGHT, TOXICITY_HIGH): 6,
}

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
EMPTY_POLITICAL_PARTY = ""
TRAINING_ASSISTED_CONDITION = "training_assisted"
USER_ID_PREFIX = "user-"
USER_ID_WIDTH = 4
CSV_INDEX = False
CSV_ENCODING = "utf-8"
S3_URI_PREFIX = "s3://"
EMPTY_CELL = ""
NAN_CELL = "nan"

PINNED_REMAINING_LABELS_S3_URI = (
    "s3://mirrorview-experimental-artifacts/"
    "experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/"
    "required_label_count_per_stimulus_post.csv"
)
PINNED_REMAINING_LABELS_SHA256 = (
    "188d627e8972d9b1ec5eb378814fd02fd588328df0a1ffc8603b0eba63d05c91"
)
PINNED_REMAINING_POST_COUNT = 18899
PINNED_REMAINING_LABEL_COUNT = 77557
PINNED_LEFT_REMAINING = 45542
PINNED_RIGHT_REMAINING = 32015

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    "experiments/generate_study_user_assignments_2026_09_08/"
    "study_user_assignments.csv"
)
DATASET_FILENAME = "study_user_assignments.csv"
SHUFFLED_FILENAME = "shuffled_stimuli.csv"
RESULTS_FILENAME = "RESULTS.md"
CACHE_DIRNAME = "cache"
CACHE_FILENAME = "remaining_labels.csv"
EXPERIMENT_DIRNAME = "generate_study_user_assignments_2026_09_08"
REMAINING_LABELS_FLAG = "--remaining-labels"

RECIPE_TEN_TEN_ODD = (2, 5, 3, 2, 5, 3)
RECIPE_TEN_TEN_EVEN = (3, 5, 2, 3, 5, 2)
RECIPE_LEFT_ONLY_ODD = (4, 10, 6, 0, 0, 0)
RECIPE_LEFT_ONLY_EVEN = (6, 10, 4, 0, 0, 0)

MISSING_REMAINING_LABELS_ERROR = (
    "missing --remaining-labels. Pass "
    f"{PINNED_REMAINING_LABELS_S3_URI}"
)


class FeedKind(str, Enum):
    """Which party mix a 20-post feed uses."""

    TEN_TEN = "ten_ten"
    LEFT_ONLY = "left_only"


@dataclass(frozen=True)
class RemainingLabelsSource:
    """Pinned remaining-label CSV identity."""

    s3_uri: str
    sha256: str
    expected_post_count: int
    expected_label_count: int


@dataclass(frozen=True)
class JoinedPost:
    """One remaining-label post joined to a catalog cell."""

    post_id: str
    remaining: int
    cell: int
    sampled_stance: str
    sample_toxicity_type: str


@dataclass(frozen=True)
class FeedKindCounts:
    """How many 10:10 and left-only feeds remaining labels can fill."""

    ten_ten_count: int
    left_only_count: int
    leftover_left_remaining: int
    user_count: int


@dataclass(frozen=True)
class UserAssignment:
    """One user's 20-post feed."""

    user_id: int
    post_ids: tuple[str, ...]
    feed_kind: FeedKind
    cell_counts: tuple[int, int, int, int, int, int]


@dataclass(frozen=True)
class LocalCsvWrite:
    """Local CSV path and file bytes."""

    path: Path
    body: bytes


@dataclass(frozen=True)
class AssignmentRunResult:
    """Counts and paths from one assignment run."""

    ten_ten_count: int
    left_only_count: int
    user_count: int
    assignment_rows: int
    assignment_slots: int
    extra_labels: int
    extra_left: int
    extra_right: int
    unused_remaining: int
    remaining_by_cell: tuple[int, int, int, int, int, int]
    assigned_by_cell: tuple[int, int, int, int, int, int]
    local_path: str
    s3_uri: str
    csv_sha256: str


PINNED_REMAINING_LABELS = RemainingLabelsSource(
    s3_uri=PINNED_REMAINING_LABELS_S3_URI,
    sha256=PINNED_REMAINING_LABELS_SHA256,
    expected_post_count=PINNED_REMAINING_POST_COUNT,
    expected_label_count=PINNED_REMAINING_LABEL_COUNT,
)


def pinned_remaining_labels() -> RemainingLabelsSource:
    """Return the pinned remaining-label CSV identity."""
    return PINNED_REMAINING_LABELS
