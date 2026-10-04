"""Settings for the balanced keep and remove GEPA ablation.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/dspy_gepa_balanced_labels_2026_10_02/src/step1_setup/main.py
"""

from __future__ import annotations

S3_BUCKET = "mirrorview-experimental-artifacts"
S3_PREFIX = "experiments/dspy_gepa_balanced_labels_2026_10_02/"
INPUT_PREFIX = f"{S3_PREFIX}inputs/"
WANDB_PROJECT_PATH = "mind_technology_lab/dspy_gepa_balanced_labels_2026_10_02"
RANDOM_SEED = 20261002
COHORT_ROW_COUNT = 405
COHORT_KEEP_COUNT = 203
COHORT_REMOVE_COUNT = 202
FINISHED_S3_PREFIX = "experiments/dspy_gepa_optimization_2026_09_30/"

OPTIMIZATION_SPLIT = "optimization"
GEPA_VALIDATION_SPLIT = "gepa_validation"
DEVELOPMENT_SPLIT = "development"
TEST_SPLIT = "test"
SPLIT_NAMES = (
    OPTIMIZATION_SPLIT,
    GEPA_VALIDATION_SPLIT,
    DEVELOPMENT_SPLIT,
    TEST_SPLIT,
)
SPLIT_KEEP_COUNTS = {
    OPTIMIZATION_SPLIT: 111,
    GEPA_VALIDATION_SPLIT: 31,
    DEVELOPMENT_SPLIT: 30,
    TEST_SPLIT: 31,
}
SPLIT_REMOVE_COUNTS = {
    OPTIMIZATION_SPLIT: 111,
    GEPA_VALIDATION_SPLIT: 30,
    DEVELOPMENT_SPLIT: 31,
    TEST_SPLIT: 30,
}
BALANCED_VALIDATION_KEEP_COUNT = 5
BALANCED_VALIDATION_REMOVE_COUNT = 5
SMOKE_METRIC_CALLS = 30
PILOT_METRIC_CALLS = 1000
PILOT_RUN_ID = "study2-gepa-balanced-2026-10-02-pilot"
COST_LIMIT_USD = 18.0
