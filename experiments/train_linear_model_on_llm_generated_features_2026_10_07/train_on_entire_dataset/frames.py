"""Join split-label rows to the 30 binary LLM feature columns."""

from __future__ import annotations

import pandas as pd

from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.constants import (
    FEATURE_COLUMNS,
    ID_COLUMN,
    LABEL_COLUMN,
    MODELING_PREFIX,
    PROPORTION_COLUMN,
    RATER_COUNT_COLUMN,
    REMOVE_COUNT_COLUMN,
    REQUIRED_LABELERS,
)


def modeling_frame(labels: pd.DataFrame, features: pd.DataFrame) -> pd.DataFrame:
    """Return label rows in their input order, with one binary column per feature.

    Raises
    ------
    ValueError
        When a row does not have five labelers, a feature column is missing,
        or a label row has no feature row.
    """
    label_rows = labels.copy()
    label_rows[ID_COLUMN] = label_rows[ID_COLUMN].astype(str)
    if label_rows[RATER_COUNT_COLUMN].ne(REQUIRED_LABELERS).any():
        raise ValueError(f"every row must have {REQUIRED_LABELERS} labelers")
    missing = [column for column in FEATURE_COLUMNS if column not in features.columns]
    if missing:
        raise ValueError(f"missing feature columns: {missing}")
    feature_rows = features.loc[:, [ID_COLUMN, *FEATURE_COLUMNS]].copy()
    feature_rows[ID_COLUMN] = feature_rows[ID_COLUMN].astype(str)
    merged = label_rows.merge(feature_rows, on=ID_COLUMN, how="left", validate="many_to_one")
    if merged[FEATURE_COLUMNS[0]].isna().any():
        raise ValueError("a label row has no feature row")
    merged[LABEL_COLUMN] = merged[LABEL_COLUMN].astype(int)
    merged[REMOVE_COUNT_COLUMN] = merged[REMOVE_COUNT_COLUMN].astype(int)
    merged[RATER_COUNT_COLUMN] = merged[RATER_COUNT_COLUMN].astype(int)
    merged[PROPORTION_COLUMN] = merged[REMOVE_COUNT_COLUMN] / merged[RATER_COUNT_COLUMN]
    for column in FEATURE_COLUMNS:
        merged[column] = merged[column].astype("int8")
    return merged.loc[:, [*MODELING_PREFIX, *FEATURE_COLUMNS]].reset_index(drop=True)
