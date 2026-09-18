"""Pinned constants for the September 2026 completion-code participant lookup.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

    PYTHONPATH=. uv run python experiments/investigate_completion_code_participants_2026_09_11/run.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from lib.constants import REPO_ROOT

EXPERIMENT_DIRNAME = "investigate_completion_code_participants_2026_09_11"
EXPERIMENT_DIR = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME

AWS_REGION = "us-east-2"
STUDY_BUCKET = "jspsych-mirror-view-2026-09-09"
STUDY_ID = "mirrorview"
STUDY_ITERATION_ID = "mirrorview_2026_09_09"
USER_ASSIGNMENTS_TABLE = "user_assignments"
DATA_PREFIX_PROLIFIC = "data/prolific/"
DATA_PREFIX_TEST = "data/test/"
ASSIGNMENT_BATCH_KEY_PREFIX = (
    "precomputed_assignments/2026_09_09-23:06:02/"
    "democrat/training_assisted/assignments.csv"
)

COMPLETION_CODE = "CE5XLP3L"
COMPLETION_LINK = "https://app.prolific.com/submissions/complete?cc=CE5XLP3L"

EXPECTED_SCORED_TRIALS = 20
MODERATION_TRIAL_TYPE = "moderation-trial"
POST_ID_COLUMN = "post_id"
TRIAL_TYPE_COLUMN = "trial_type"
DECISION_COLUMN = "decision"
PROLIFIC_ID_COLUMN = "prolific_id"
ATTENTION_PASSED_COLUMN = "attention_check_passed"
ATTENTION_SELECTED_COLUMN = "attention_check_selected"
CONSENTED_COLUMN = "consented"
PARTY_GROUP_COLUMN = "party_group"
CONDITION_COLUMN = "condition"
REFLECTION_COLUMN = "phase1_pair_reflection_text"
AGE_COLUMN = "age"
IDEOLOGY_COLUMN = "political_ideology"
ATTITUDE_COLUMN = "attitude_reduce_abortion"
TIME_ELAPSED_COLUMN = "time_elapsed"
TRIAL_INDEX_COLUMN = "trial_index"
ASSIGNMENT_ID_COLUMN = "id"
ASSIGNED_POST_IDS_COLUMN = "assigned_post_ids"

DEFAULT_PROLIFIC_IDS: tuple[str, ...] = (
    "671be80dd312fef1ab1d7c31",
    "69f769601fc86e145904de9a",
)

RESULTS_FILENAME = "RESULTS.md"
FINDINGS_JSON_FILENAME = "findings.json"
OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_KEY = (
    f"experiments/{EXPERIMENT_DIRNAME}/findings.json"
)
SAVE_DATA_LOG_GROUP = "/aws/lambda/jspsych-scroll-save-data"

PYTEST_COMMAND = (
    "PYTHONPATH=. uv run pytest "
    "experiments/investigate_completion_code_participants_2026_09_11/tests -q"
)
RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/investigate_completion_code_participants_2026_09_11/run.py"""


@dataclass(frozen=True)
class AssignmentRecord:
    """One DynamoDB user_assignments row, or a miss."""

    prolific_id: str
    found: bool
    created_at: str | None
    study_iteration_id: str | None
    assignment_id: str | None
    political_party: str | None
    condition: str | None
    assignment_s3_key: str | None


@dataclass(frozen=True)
class SessionFile:
    """One jsPsych CSV object that contains the participant id."""

    key: str
    last_modified: str
    size: int


@dataclass(frozen=True)
class SessionSummary:
    """Completeness fields from one saved jsPsych CSV."""

    prolific_id: str
    n_rows: int
    n_scored_moderation: int
    unique_scored_posts: int
    scored_post_ids: tuple[str, ...]
    decision_counts: tuple[tuple[str, int], ...]
    attention_check_passed: int | None
    attention_check_selected: str | None
    consented: int | None
    party_group: str | None
    condition: str | None
    has_reflection: bool
    reflection_word_count: int
    has_demographics: bool
    has_ideology: bool
    has_attitudes: bool
    time_elapsed_ms: float | None
    trial_index_max: int | None
    is_complete: bool


@dataclass(frozen=True)
class ParticipantFinding:
    """Assignment + saved session + recommendation for one Prolific id."""

    prolific_id: str
    assignment: AssignmentRecord
    session_files: tuple[SessionFile, ...]
    session: SessionSummary | None
    assigned_post_ids: tuple[str, ...] | None
    posts_match_assignment: bool | None
    recommendation: str


@dataclass(frozen=True)
class InvestigationResult:
    """Live lookup output written to RESULTS.md."""

    findings: tuple[ParticipantFinding, ...]
    prolific_csv_count: int
    findings_s3_uri: str
    findings_sha256: str
    results_path: Path
