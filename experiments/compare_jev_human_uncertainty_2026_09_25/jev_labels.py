"""Load the stored Jev remove probabilities.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
"""

from __future__ import annotations

import os
from io import BytesIO

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    EXPECTED_JEV_ROWS,
    JEV_BIN_EDGES,
    JEV_BUCKET,
    JEV_LABELS_KEY,
)
from lib.aws.s3 import DEFAULT_REGION_NAME, S3

_JEV_COLUMNS = ("post_id", "p_remove")


def use_lab_credentials() -> None:
    """Copy lab AWS keys into the standard env vars when those are empty."""
    if not os.environ.get("AWS_ACCESS_KEY_ID"):
        access_key = os.environ.get("LAB_AWS_ACCESS_KEY_ID", "")
        if access_key:
            os.environ["AWS_ACCESS_KEY_ID"] = access_key
    if not os.environ.get("AWS_SECRET_ACCESS_KEY"):
        secret_key = os.environ.get("LAB_AWS_ACCESS_KEY_SECRET", "")
        if secret_key:
            os.environ["AWS_SECRET_ACCESS_KEY"] = secret_key


def _require_jev_columns(labels: pd.DataFrame) -> None:
    """Raise KeyError when a Jev label column is missing."""
    missing = [name for name in _JEV_COLUMNS if name not in labels.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")


def _require_jev_row_count(labels: pd.DataFrame) -> None:
    """Raise ValueError when the row count is not the pinned size."""
    if len(labels) != EXPECTED_JEV_ROWS:
        raise ValueError(f"expected {EXPECTED_JEV_ROWS} Jev rows, found {len(labels)}")


def _require_unique_post_ids(labels: pd.DataFrame) -> None:
    """Raise ValueError when post_id is duplicated."""
    if labels["post_id"].duplicated().any():
        raise ValueError("duplicate post_id in Jev labels")


def _require_probabilities(labels: pd.DataFrame) -> None:
    """Raise ValueError when a probability is missing or out of range."""
    if labels["p_remove"].isna().any():
        raise ValueError("p_remove has missing values")
    values = labels["p_remove"].astype(float)
    out_of_range = (values < JEV_BIN_EDGES[0]) | (values > JEV_BIN_EDGES[-1])
    if out_of_range.any():
        raise ValueError("p_remove outside 0 to 1")


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
    _require_jev_columns(labels)
    _require_jev_row_count(labels)
    _require_unique_post_ids(labels)
    _require_probabilities(labels)


def load_jev_labels() -> pd.DataFrame:
    """Download the stored Jev label file and check it.

    Returns
    -------
    pandas.DataFrame
        The checked label frame.
    """
    use_lab_credentials()
    store = S3(JEV_BUCKET, region_name=DEFAULT_REGION_NAME)
    labels = pd.read_parquet(BytesIO(store.get_bytes(JEV_LABELS_KEY)))
    assert_jev_label_frame(labels)
    return labels
