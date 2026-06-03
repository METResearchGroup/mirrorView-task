"""Train/test splitting for simplified keep/remove training."""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split


def make_train_test_split(
    df: pd.DataFrame,
    *,
    train_split: float = 0.8,
    seed: int = 42,
    label_column: str = "keep_remove_label",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Stratified split on ``keep_remove_label`` (or ``label_column``)."""
    if label_column not in df.columns:
        raise KeyError(f"Missing label column {label_column!r}")
    if not 0.0 < train_split < 1.0:
        raise ValueError("train_split must be between 0 and 1 (exclusive).")
    return train_test_split(
        df,
        train_size=train_split,
        stratify=df[label_column],
        random_state=seed,
    )
