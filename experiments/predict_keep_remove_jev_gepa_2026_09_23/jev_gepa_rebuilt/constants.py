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
SMOKE_JEV_POSTS = 100
SMOKE_METRIC_CALLS = 120
SMOKE_VAL_SUBSAMPLE_SIZE = 20
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
EXPERIMENT_ROOT = Path("experiments/predict_keep_remove_jev_gepa_2026_09_23")
DEV_AB_SPLIT_RELATIVE = Path("data/dev_ab_split.json")
TOP_ACCEPTED_CANDIDATES = 10
MAX_OPTIMIZED_COMPONENT_CHARS = 4000
TRAIN_QUOTE_MIN_SUBSTRING_LEN = 40
VAL_DEV_GAP_MAX = 0.15
DEV_B_CONFIRM_MAX_F1_DROP = 0.02
ACCEPTANCE_LOG_FILENAME = "acceptance_log.jsonl"
REFLECTION_USD_PER_MILLION = {
    "openai/gpt-6-luna": (0.10, 0.50),
    "openai/gpt-5.6-terra": (2.0, 12.0),
}
MAX_REFLECTION_COST_USD = {
    "openai/gpt-6-luna": 5.0,
    "openai/gpt-5.6-terra": 40.0,
}
HALF_BUDGET_MAX_REFLECTION_COST_USD = 2.50
REFLECTION_USAGE_JSONL = "reflection_usage.jsonl"
STOP_REASON_FILENAME = "stop_reason.json"
COMPONENT_UPDATE_LOG_FILENAME = "component_update_log.jsonl"
R4_ROUND_ROBIN_COMPONENT_KEYS = (
    STUDY_COMPONENT_KEY,
    "remove_criteria",
    "keep_criteria",
    "mirror_note",
)
R4_SEED_REMOVE_CRITERIA = "- Personal attacks or slurs.\n- Calls for violence."
R4_SEED_KEEP_CRITERIA = "- Good-faith policy argument.\n- News reporting with context."
R4_SEED_MIRROR_NOTE = "Mirror post is opposite stance."
SMOKE_OUTPUT_DIR = OUTPUT_ROOT / "_smoke"
R1_SMOKE_REPORT_FILENAME = "r1_smoke_report.json"
R4_SMOKE_PASSED_FILENAME = "r4_smoke_passed.json"
