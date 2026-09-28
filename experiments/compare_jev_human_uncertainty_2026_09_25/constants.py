"""Pinned counts and column names for the Jev and human comparison.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
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
JEV_BIN_COUNT = REQUIRED_LABELERS + 1
JEV_BIN_EDGES = tuple(index / JEV_BIN_COUNT for index in range(JEV_BIN_COUNT + 1))
COMPARISON_COLUMNS = ("post_id", "n_remove", "p_remove", "jev_bin", "difference_score")
EXPECTED_JEV_BIN_COUNTS = (646, 5575, 3578, 2729, 2090, 495)
PROBABILITY_HIST_BINS = 20
DIFFERENCE_SCORE_MIN = -REQUIRED_LABELERS
DIFFERENCE_SCORE_MAX = REQUIRED_LABELERS
EXPECTED_MEAN_DIFFERENCE = -0.6147
FIGURE_DIRNAME = "outputs/figures"
TABLE_DIRNAME = "outputs/tables"
JOINED_FILENAME = "outputs/joined.parquet"
RESULTS_FILENAME = "RESULTS.md"
Y_AXIS_LABEL = "Posts"
BAR_WIDTH = 0.4
FIGURE_FILENAMES = (
    "human_remove_counts.png",
    "jev_probability.png",
    "jev_six_bins.png",
    "overlay_human_vs_jev.png",
    "difference_score.png",
)
TABLE_FILENAMES = (
    "human_remove_counts.csv",
    "jev_bins.csv",
    "difference_scores.csv",
    "remove_by_jev_bin.csv",
)
