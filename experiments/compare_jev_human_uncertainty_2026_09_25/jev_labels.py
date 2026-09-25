"""Load the stored Jev remove probabilities.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_jev_bins.py -q
"""

from __future__ import annotations

import pandas as pd


def assert_jev_label_frame(labels: pd.DataFrame) -> None:
    """Require a complete Jev label file.

    Parameters
    ----------
    labels
        Stored per-post Jev probabilities.

    Raises
    ------
    ValueError
        When the row count, post ids, or probabilities fail the pinned checks.
    KeyError
        When ``post_id`` or ``p_remove`` is missing.
    """
    raise NotImplementedError


def load_jev_labels() -> pd.DataFrame:
    """Download the stored Jev label file and check it.

    Returns
    -------
    pandas.DataFrame
        The checked label frame.
    """
    raise NotImplementedError
