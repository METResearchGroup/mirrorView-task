"""Compute remaining labels for old posts and the new 10,000 row catalog."""

from __future__ import annotations

import pandas as pd


def calculate_required_label_counts(
    old_catalog: pd.DataFrame,
    old_results: pd.DataFrame,
    new_catalog: pd.DataFrame,
    required_labels_per_post: int,
) -> pd.DataFrame:
    """Return remaining label counts for old and new posts.

    Raises
    ------
    ValueError
        When the same id appears in both batches.
    """
    raise NotImplementedError
