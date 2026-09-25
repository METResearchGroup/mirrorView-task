"""Load the stored Jev remove probabilities.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py -q
"""

from __future__ import annotations

import pandas as pd


def assert_jev_label_frame(labels: pd.DataFrame) -> None:
    raise NotImplementedError


def load_jev_labels() -> pd.DataFrame:
    raise NotImplementedError
