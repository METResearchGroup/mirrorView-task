"""Feature construction for training on original embeddings only."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from experiments.simplified_predict_remove_2026_05_13.features import (
    JOIN_COL_ORIGINAL,
    classification_metrics_summary,
)


@dataclass
class OnlyOriginalEmbeddingFeatureBuilder:
    """Build X from original embeddings only."""

    embedding_dim: int | None = None
    _feature_names: list[str] | None = None

    def fit(self, df: pd.DataFrame) -> "OnlyOriginalEmbeddingFeatureBuilder":
        if JOIN_COL_ORIGINAL not in df.columns:
            raise KeyError(f"Missing required join column {JOIN_COL_ORIGINAL!r}")
        if len(df) == 0:
            raise ValueError("Cannot fit feature builder on empty dataframe.")

        o0 = np.asarray(df[JOIN_COL_ORIGINAL].iloc[0], dtype=np.float64).ravel()
        self.embedding_dim = int(o0.shape[0])
        self._feature_names = [f"orig_{i}" for i in range(self.embedding_dim)]
        return self

    def feature_names_(self) -> list[str]:
        if self._feature_names is None or self.embedding_dim is None:
            raise RuntimeError("Call fit() before reading feature_names_.")
        return self._feature_names

    def transform(self, df: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        if self.embedding_dim is None or self._feature_names is None:
            raise RuntimeError("Call fit() before transform().")
        if len(df) == 0:
            raise ValueError("Cannot transform empty dataframe.")

        o = np.vstack(df[JOIN_COL_ORIGINAL].to_numpy()).astype(np.float64, copy=False)
        if o.shape[1] != self.embedding_dim:
            raise ValueError(
                "Embedding dimensionality mismatch after fit: "
                f"expected={self.embedding_dim} got orig={o.shape[1]}"
            )
        return o, list(self._feature_names)


def build_xy_from_joined(
    df: pd.DataFrame,
    feature_builder: OnlyOriginalEmbeddingFeatureBuilder,
    *,
    label_column: str = "keep_remove_label",
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    if label_column not in df.columns:
        raise KeyError(f"Missing label column {label_column!r}")
    x, feature_names = feature_builder.transform(df)
    y = df[label_column].astype(np.int64).values
    return x, y, feature_names


def classification_metrics_summary_reexport(y_true, y_pred, pos_scores) -> dict[str, float]:
    return classification_metrics_summary(y_true, y_pred, pos_scores)
