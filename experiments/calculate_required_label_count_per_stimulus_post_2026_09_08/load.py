"""Load the old catalog, old results, and new sample parquet.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import pandas as pd


def load_old_catalog() -> pd.DataFrame:
    """Load unique ids from the old stimulus catalog."""
    raise NotImplementedError


def load_old_results() -> pd.DataFrame:
    """Load the old study results used to count unique raters."""
    raise NotImplementedError


def load_new_sample(source: object) -> pd.DataFrame:
    """Download the pinned new sample parquet and check its identity."""
    raise NotImplementedError
