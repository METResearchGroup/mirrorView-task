"""Fit and score the modal-label and remove-share regressions."""

from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    precision_score,
    r2_score,
    recall_score,
    root_mean_squared_error,
)

from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.constants import (
    FEATURE_COLUMNS,
    LABEL_COLUMN,
    LOGISTIC_MAX_ITER,
    LOGISTIC_RANDOM_STATE,
    LOGISTIC_THRESHOLD,
    PROPORTION_COLUMN,
)


def feature_matrix(frame: pd.DataFrame) -> np.ndarray:
    """Return the feature columns in ``FEATURE_COLUMNS`` order."""
    return frame.loc[:, list(FEATURE_COLUMNS)].to_numpy()


def fit_logistic(train: pd.DataFrame) -> LogisticRegression:
    """Fit the modal-label logistic regression without reordering rows."""
    estimator = LogisticRegression(
        solver="lbfgs",
        max_iter=LOGISTIC_MAX_ITER,
        random_state=LOGISTIC_RANDOM_STATE,
    )
    estimator.fit(feature_matrix(train), train[LABEL_COLUMN].astype(int).to_numpy())
    return estimator


def fit_linear(train: pd.DataFrame) -> LinearRegression:
    """Fit the remove-share linear regression without clipping and without reordering."""
    estimator = LinearRegression(fit_intercept=True)
    estimator.fit(
        feature_matrix(train).astype(float),
        train[PROPORTION_COLUMN].astype(float).to_numpy(),
    )
    return estimator


def remove_probability(estimator: LogisticRegression, frame: pd.DataFrame) -> np.ndarray:
    """Return the predicted probability of the remove class."""
    probabilities = estimator.predict_proba(feature_matrix(frame))
    class_index = list(estimator.classes_).index(1)
    return probabilities[:, class_index]


def hard_remove_label(estimator: LogisticRegression, frame: pd.DataFrame) -> np.ndarray:
    """Return 1 when the remove probability is at least 0.5."""
    return (remove_probability(estimator, frame) >= LOGISTIC_THRESHOLD).astype(int)


def clip_proportion(values: np.ndarray) -> np.ndarray:
    """Limit each prediction to the closed range 0 to 1."""
    return np.clip(np.asarray(values, dtype=float), 0.0, 1.0)


def logistic_metrics(y_true: np.ndarray, y_hat: np.ndarray) -> dict[str, float]:
    """Return accuracy, precision, recall, F1, and the constant-keep accuracy."""
    y_true = np.asarray(y_true, dtype=int)
    y_hat = np.asarray(y_hat, dtype=int)
    return {
        "sample_count": float(len(y_true)),
        "accuracy": float(accuracy_score(y_true, y_hat)),
        "precision": float(precision_score(y_true, y_hat, pos_label=1, zero_division=0)),
        "recall": float(recall_score(y_true, y_hat, pos_label=1, zero_division=0)),
        "f1": float(f1_score(y_true, y_hat, pos_label=1, zero_division=0)),
        "constant_keep_accuracy": float(np.mean(y_true == 0)),
    }


def linear_metrics(y_true: np.ndarray, y_raw: np.ndarray) -> dict[str, float]:
    """Score the clipped predictions and count raw predictions outside 0 to 1."""
    y_true = np.asarray(y_true, dtype=float)
    y_raw = np.asarray(y_raw, dtype=float)
    clipped = clip_proportion(y_raw)
    outside = int(np.sum((y_raw < 0.0) | (y_raw > 1.0)))
    return {
        "sample_count": float(len(y_true)),
        "mae": float(mean_absolute_error(y_true, clipped)),
        "rmse": float(root_mean_squared_error(y_true, clipped)),
        "r2": float(r2_score(y_true, clipped)),
        "outside_count": float(outside),
    }


def coefficient_frame(feature_names: tuple[str, ...], intercept: float, weights: np.ndarray) -> pd.DataFrame:
    """Return the intercept first, then one row per feature in model order."""
    rows = [{"feature": "intercept", "coefficient": float(intercept)}]
    for name, weight in zip(feature_names, np.asarray(weights, dtype=float), strict=True):
        rows.append({"feature": name, "coefficient": float(weight)})
    return pd.DataFrame(rows)
