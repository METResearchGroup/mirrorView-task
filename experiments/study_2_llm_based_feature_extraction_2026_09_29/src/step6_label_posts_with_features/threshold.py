"""Turn Jev probabilities into 0 or 1 feature columns."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    LABEL_COLUMNS_PREFIX,
)


def probabilities_frame(
    predictions_path: Path,
    sha: str,
    label_keys: list[str],
) -> pd.DataFrame:
    """Read one probability row per post for the current feature-list hash.

    Parameters
    ----------
    predictions_path
        JSONL predictions.
    sha
        Current feature-list hash. Older lines are ignored.
    label_keys
        Feature columns that must be present.

    Returns
    -------
    pandas.DataFrame
        ``post_id`` plus one float column per label key.

    Raises
    ------
    ValueError
        When a post id is duplicated or a label key is missing.
    """
    rows: list[dict[str, object]] = []
    for line in predictions_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        record = json.loads(line)
        if record.get("features_sha256") != sha:
            continue
        row: dict[str, object] = {"post_id": str(record["post_id"])}
        probabilities = record["probabilities"]
        for key in label_keys:
            if key not in probabilities:
                raise ValueError(f"missing key {key} for post {row['post_id']}")
            row[key] = float(probabilities[key])
        rows.append(row)
    frame = pd.DataFrame.from_records(rows)
    if frame["post_id"].duplicated().any():
        raise ValueError("duplicate post_id in predictions")
    return frame


def apply_threshold(probabilities: pd.DataFrame, threshold: float) -> pd.DataFrame:
    """Set a feature to 1 when its probability is at least the cutoff.

    Parameters
    ----------
    probabilities
        Frame from :func:`probabilities_frame`.
    threshold
        Inclusive cutoff. The experiment uses 0.7.

    Returns
    -------
    pandas.DataFrame
        Same columns, with feature values as ``int8``.
    """
    labels = probabilities.copy()
    feature_columns = [column for column in labels.columns if column != "post_id"]
    for column in feature_columns:
        labels[column] = (labels[column] >= threshold).astype("int8")
    return labels


def build_label_table(labels: pd.DataFrame, pairs: pd.DataFrame) -> pd.DataFrame:
    """Join 0 or 1 labels to the pair text columns.

    Parameters
    ----------
    labels
        Thresholded feature columns.
    pairs
        Stimulus rows with ``post_id``, ``original_text``, and ``mirror_text``.

    Returns
    -------
    pandas.DataFrame
        Prefix columns, then label keys in sorted order.
    """
    merged = labels.merge(
        pairs.loc[:, ["post_id", "original_text", "mirror_text"]],
        on="post_id",
        how="left",
    )
    feature_columns = sorted(column for column in labels.columns if column != "post_id")
    ordered = ["post_id", "original_text", "mirror_text", *feature_columns]
    missing = [column for column in LABEL_COLUMNS_PREFIX if column not in ordered]
    if missing:
        raise ValueError(f"missing prefix columns: {missing}")
    return merged.loc[:, list(LABEL_COLUMNS_PREFIX) + feature_columns]
