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
