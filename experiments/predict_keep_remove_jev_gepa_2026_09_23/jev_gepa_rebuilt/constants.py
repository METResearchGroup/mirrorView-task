"""Pinned constants for rebuilt GEPA on the union cohort.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_constants.py -q
"""

from __future__ import annotations

from pathlib import Path

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import COHORT_UNION_PARQUET

WANDB_GROUP = "jev_gepa_rebuilt"
REBUILT_S3_SUBPREFIX = "jev_gepa_rebuilt"
DEFAULT_MAX_METRIC_CALLS = 30_000
HALF_BUDGET_MAX_METRIC_CALLS = 15_000
GEPA_SEED = 20260924
REFLECTION_MINIBATCH_SIZE = 25
VAL_SUBSAMPLE_SIZE = 100
ACCEPTANCE_MARGIN_CORRECT = 2
STUDY_COMPONENT_KEY = "study_instruction"
OUTPUT_ROOT = Path(
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/outputs"
)
GEPA_RUN_DIRNAME = "gepa_run"
GEPA_RESULT_FILENAME = "gepa_result.json"
DEV_SELECTION_FILENAME = "dev_selection.json"
CANDIDATE_DEV_SCORES_FILENAME = "candidate_dev_scores.jsonl"
