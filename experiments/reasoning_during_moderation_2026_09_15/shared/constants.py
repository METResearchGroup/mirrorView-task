"""Pinned paths and counts for the reasoning-during-moderation experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

from lib.constants import REPO_ROOT

SINCE_DATE = date(2026, 9, 9)
STUDY_BUCKET = "jspsych-mirror-view-2026-09-09"
STUDY_PREFIX = "data/prolific/"
OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
EXPERIMENT_DIRNAME = "reasoning_during_moderation_2026_09_15"
EXPERIMENT_S3_PREFIX = f"experiments/{EXPERIMENT_DIRNAME}"
COHORT_FILENAME = "three_group_cohort.parquet"
SLIM_TRIALS_FILENAME = "slim_trials.parquet"
METADATA_FILENAME = "export_metadata.json"
COHORT_S3_KEY = f"{EXPERIMENT_S3_PREFIX}/outputs/cohort/{COHORT_FILENAME}"
SLIM_TRIALS_S3_KEY = f"{EXPERIMENT_S3_PREFIX}/outputs/cohort/{SLIM_TRIALS_FILENAME}"
METADATA_S3_KEY = f"{EXPERIMENT_S3_PREFIX}/outputs/cohort/{METADATA_FILENAME}"
PAIR_ORDER_SEED = 0
PAIR_ORDER_BIN_COUNT = 2
ORIGINAL_FIRST_DRAW = 0
PAIR_ORDER_HASH_BYTES = 8
MIN_CSV_FILES = 3075
MIN_RATERS = 4
SNAPSHOT_SPLIT_COUNT = 2200
SNAPSHOT_UNANIMOUS_KEEP_COUNT = 2256
SNAPSHOT_UNANIMOUS_REMOVE_COUNT = 208
ROLE_ORIGINAL = "original"
ROLE_MIRROR = "mirror"
GROUP_SPLIT = "split"
GROUP_UNANIMOUS_KEEP = "unanimous_keep"
GROUP_UNANIMOUS_REMOVE = "unanimous_remove"
DECISION_KEEP = "keep"
DECISION_REMOVE = "remove"
EVALUATION_MODE_LINKED_FATE = "linked_fate"
TRIAL_TYPE_MODERATION = "moderation-trial"
EMPTY_POST_SENTINEL = "nan"
PAIR_ORDER_ORIGINAL_FIRST = (ROLE_ORIGINAL, ROLE_MIRROR)
PAIR_ORDER_MIRROR_FIRST = (ROLE_MIRROR, ROLE_ORIGINAL)
SPLIT_VOTE_PATTERNS = frozenset({(2, 2), (3, 2), (2, 3)})
COHORT_COLUMNS = (
    "post_id",
    "original_text",
    "mirror_text",
    "group",
    "n_raters",
    "keep_count",
    "remove_count",
    "post_1_role",
    "post_2_role",
)
SLIM_TRIAL_COLUMNS = (
    "post_id",
    "prolific_id",
    "decision",
    "response_time_ms",
    "trial_index",
    "time_elapsed",
    "group",
)
REQUIRED_SLIM_COLUMNS = (
    "evaluation_mode",
    "decision",
    "post_id",
    "prolific_id",
    "trial_type",
    "original_text",
    "mirror_text",
)
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
COHORT_OUTPUT_DIR = EXPERIMENT_DIR / "outputs" / "cohort"

QWEN_MODEL_ID = "Qwen/Qwen3.5-4B"
DEEPSEEK_MODEL_ID = "deepseek-ai/DeepSeek-R1-Distill-Qwen-7B"
PROMPT_ARM_STUDY = "study"
PROMPT_ARM_CRITERIA = "study_plus_criteria"
STATUS_VALID = "valid"
STATUS_EMPTY_THINKING = "empty_thinking"
STATUS_MISSING_CLOSE_TAG = "missing_close_tag"
STATUS_TRUNCATED = "truncated"
STATUS_INFRASTRUCTURE = "infrastructure"
THINK_OPEN_TAG = "<think>"
THINK_CLOSE_TAG = "</think>"
THINK_OPEN_SUFFIX = "<think>\n"
SMOKE_MAX_NEW_TOKENS = 2048
FULL_MAX_NEW_TOKENS = 8192
SMOKE_LIMIT = 3
GENERATION_SEED_BYTES = 4
UINT32_MODULUS = 2**32
QWEN_TEMPERATURE = 1.0
QWEN_TOP_P = 0.95
QWEN_TOP_K = 20
QWEN_MIN_P = 0.0
QWEN_PRESENCE_PENALTY = 1.5
QWEN_REPETITION_PENALTY = 1.0
DEEPSEEK_TEMPERATURE = 0.6
DEEPSEEK_TOP_P = 0.95
HF_JOB_FLAVOR = "l4x1"
HF_JOB_TIMEOUT = "24h"
HF_JOB_PYTHON = "3.12"
CLOSING_LINE = "Allow or Remove?"
POST_1_LABEL = "Post 1:"
POST_2_LABEL = "Post 2:"


class GroupName(str, Enum):
    """Analysis group for an eligible post."""

    SPLIT = GROUP_SPLIT
    UNANIMOUS_KEEP = GROUP_UNANIMOUS_KEEP
    UNANIMOUS_REMOVE = GROUP_UNANIMOUS_REMOVE


class PostRole(str, Enum):
    """Which member of a linked-fate pair is shown as Post 1 or Post 2."""

    ORIGINAL = ROLE_ORIGINAL
    MIRROR = ROLE_MIRROR


@dataclass(frozen=True)
class CohortCounts:
    """Printed group sizes after the cohort build."""

    csv_files: int
    split: int
    unanimous_keep: int
    unanimous_remove: int
    eligible_posts: int


@dataclass(frozen=True)
class PairOrder:
    """Stored Post 1 and Post 2 roles for one post."""

    post_1_role: str
    post_2_role: str


@dataclass(frozen=True)
class CohortRunResult:
    """Local and S3 artifacts from one cohort build."""

    counts: CohortCounts
    local_cohort_path: Path
    local_slim_path: Path
    local_metadata_path: Path
    cohort_s3_uri: str
    sha256: str


@dataclass(frozen=True)
class ThinkingCount:
    """Token-id count for one generated thinking span."""

    status: str
    thinking_token_count: int
    close_tag_index: int | None


@dataclass(frozen=True)
class SamplingConfig:
    """Generation sampling values for one model."""

    temperature: float
    top_p: float
    top_k: int | None
    min_p: float | None
    presence_penalty: float | None
    repetition_penalty: float | None
