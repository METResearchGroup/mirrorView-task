"""Compute remaining labels for old and new stimulus posts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import pandas as pd


def calculate_required_label_counts(
    old_catalog: pd.DataFrame,
    old_results: pd.DataFrame,
    new_sample: pd.DataFrame,
) -> pd.DataFrame:
    """Return remaining label counts for old and new posts."""
    raise NotImplementedError
