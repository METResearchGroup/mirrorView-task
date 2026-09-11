"""Pinned constants for the September 2026 study progress dashboard.

Run from the repo root:

    export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
    export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"
    PYTHONPATH=. uv run python experiments/study_progress_dashboard_2026_09_11/run.py
"""

from __future__ import annotations

from pathlib import Path

EXPERIMENT_DIRNAME = "study_progress_dashboard_2026_09_11"
CACHE_DIRNAME = "cache"
OUTPUTS_DIRNAME = "outputs"
PAYLOAD_FILENAME = "dashboard_payload.json"
DASHBOARD_FILENAME = "index.html"
RESULTS_FILENAME = "RESULTS.md"

STUDY_ID = "mirrorview"
STUDY_ITERATION_ID = "mirrorview_2026_09_09"
STUDY_BUCKET = "jspsych-mirror-view-2026-09-09"
AWS_REGION = "us-east-2"
USER_ASSIGNMENTS_TABLE = "user_assignments"

CONDITION = "training_assisted"
POSTS_PER_USER = 20
TARGET_USERS = 3879
TARGET_DEMOCRAT_SLOTS = 1940
TARGET_REPUBLICAN_SLOTS = 1939
TARGET_LABELS = 77580
TARGET_POSTS = 18899
GRACE_MINUTES = 20

PARTY_DEMOCRAT = "democrat"
PARTY_REPUBLICAN = "republican"
PARTY_ORDER = (PARTY_DEMOCRAT, PARTY_REPUBLICAN)
PARTY_LABELS = {
    PARTY_DEMOCRAT: "Democrat",
    PARTY_REPUBLICAN: "Republican",
}

DECISION_KEEP = "keep"
DECISION_REMOVE = "remove"
DECISION_ORDER = (DECISION_KEEP, DECISION_REMOVE)

TRIAL_TYPE_MODERATION = "moderation-trial"
EVALUATION_MODE_LINKED_FATE = "linked_fate"

TOXICITY_LOW = "sample_low_toxicity"
TOXICITY_MIDDLE = "sample_middle_toxicity"
TOXICITY_HIGH = "sample_high_toxicity"
TOXICITY_ORDER = (TOXICITY_LOW, TOXICITY_MIDDLE, TOXICITY_HIGH)
TOXICITY_LABELS = {
    TOXICITY_LOW: "Low",
    TOXICITY_MIDDLE: "Middle",
    TOXICITY_HIGH: "High",
}

STANCE_LEFT = "left"
STANCE_RIGHT = "right"
STANCE_ORDER = (STANCE_LEFT, STANCE_RIGHT)
STANCE_LABELS = {
    STANCE_LEFT: "Left",
    STANCE_RIGHT: "Right",
}

CELL_BY_STANCE_TOXICITY = {
    (STANCE_LEFT, TOXICITY_LOW): 1,
    (STANCE_LEFT, TOXICITY_MIDDLE): 2,
    (STANCE_LEFT, TOXICITY_HIGH): 3,
    (STANCE_RIGHT, TOXICITY_LOW): 4,
    (STANCE_RIGHT, TOXICITY_MIDDLE): 5,
    (STANCE_RIGHT, TOXICITY_HIGH): 6,
}
CELL_LABELS = {
    1: "Left, low toxicity",
    2: "Left, middle toxicity",
    3: "Left, high toxicity",
    4: "Right, low toxicity",
    5: "Right, middle toxicity",
    6: "Right, high toxicity",
}
CELL_TARGET_SLOTS = {
    1: 10463,
    2: 22001,
    3: 13096,
    4: 8796,
    5: 16594,
    6: 6630,
}

KEEP_RATE_BIN_EDGES = (0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)
KEEP_RATE_BIN_LABELS = (
    "0 to 10%",
    "10 to 20%",
    "20 to 30%",
    "30 to 40%",
    "40 to 50%",
    "50 to 60%",
    "60 to 70%",
    "70 to 80%",
    "80 to 90%",
    "90 to 100%",
)

INVALID_PROLIFIC_SUBSTRINGS = ("pid", "manual-test", "dev")

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"
OUTPUT_S3_PREFIX = f"experiments/{EXPERIMENT_DIRNAME}/"

TIMESTAMP_FORMAT = "%Y_%m_%d-%H:%M:%S"

EXPERIMENT_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPERIMENT_DIR.parent.parent


def experiment_dir() -> Path:
    """Return this experiment directory."""
    return EXPERIMENT_DIR
