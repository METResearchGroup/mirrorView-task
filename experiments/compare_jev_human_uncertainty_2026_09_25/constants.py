"""Pinned counts and column names for the Jev and human comparison.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
"""

from __future__ import annotations

EXPERIMENT_NAME = "compare_jev_human_uncertainty_2026_09_25"
REQUIRED_LABELERS = 5
DECISION_KEEP = "keep"
DECISION_REMOVE = "remove"
TRIAL_TYPE_MODERATION = "moderation-trial"
HUMAN_COUNT_COLUMNS = ("post_id", "n_raters", "n_remove")
EXPECTED_FIVE_LABELER_POSTS = 15113
EXPECTED_REMOVE_COUNTS = (3986, 4592, 3332, 1929, 950, 324)
JEV_BUCKET = "mirrorview-experimental-artifacts"
JEV_LABELS_KEY = (
    "experiments/predict_keep_remove_jev_gepa_2026_09_23/"
    "jev_baseline_union/A1_pair_study_prompt/labels.parquet"
)
EXPECTED_JEV_ROWS = 19219
JEV_BIN_EDGES = (0.0, 0.2, 0.4, 0.6, 0.8, 1.0)
JEV_BIN_COUNT = 5
COMPARISON_COLUMNS = ("post_id", "n_remove", "p_remove", "jev_bin", "difference_score")
EXPECTED_JEV_BIN_COUNTS = (1479, 6282, 3774, 2738, 840)
