"""Tests for the full split-label regression helpers."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import LinearRegression

from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.constants import (
    FEATURE_COLUMNS,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.frames import (
    modeling_frame,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.models import (
    clip_proportion,
    coefficient_frame,
    fit_linear,
    hard_remove_label,
    logistic_metrics,
)
from experiments.train_linear_model_on_llm_generated_features_2026_10_07.train_on_entire_dataset.report import (
    render_results,
)


def _labels() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": ["b", "a", "b"],
            "keep_remove_label": [0, 1, 0],
            "n_remove": [1, 4, 1],
            "n_raters": [5, 5, 5],
        }
    )


def _features() -> pd.DataFrame:
    frame = pd.DataFrame({"post_id": ["a", "b"]})
    for index, column in enumerate(FEATURE_COLUMNS):
        frame[column] = [index % 2, (index + 1) % 2]
    return frame


def test_modeling_frame_keeps_duplicate_rows_and_input_order() -> None:
    frame = modeling_frame(_labels(), _features())
    assert frame["post_id"].tolist() == ["b", "a", "b"]
    assert frame["remove_proportion"].tolist() == [0.2, 0.8, 0.2]
    assert list(frame.columns[:5]) == [
        "post_id",
        "keep_remove_label",
        "n_remove",
        "n_raters",
        "remove_proportion",
    ]
    assert tuple(frame.columns[5:]) == FEATURE_COLUMNS


def test_modeling_frame_rejects_a_missing_feature_row() -> None:
    labels = _labels()
    features = _features().iloc[:1]
    with pytest.raises(ValueError, match="no feature row"):
        modeling_frame(labels, features)


def test_hard_label_treats_one_half_as_remove() -> None:
    class Stub:
        classes_ = np.array([0, 1])

        def predict_proba(self, matrix: np.ndarray) -> np.ndarray:
            return np.array([[0.5, 0.5], [0.51, 0.49]])

    labels = hard_remove_label(Stub(), _feature_only_frame(2))
    assert labels.tolist() == [1, 0]


def test_clip_proportion_limits_the_closed_unit_interval() -> None:
    clipped = clip_proportion(np.array([-0.2, 0.4, 1.2]))
    assert clipped.tolist() == [0.0, 0.4, 1.0]


def test_constant_keep_accuracy_is_the_keep_share() -> None:
    metrics = logistic_metrics(np.array([0, 0, 1]), np.array([1, 1, 1]))
    assert metrics["constant_keep_accuracy"] == pytest.approx(2 / 3)
    assert metrics["f1"] == pytest.approx(0.5)


def test_linear_fit_does_not_clip() -> None:
    train = _feature_only_frame(4)
    train["remove_proportion"] = train[FEATURE_COLUMNS[0]].astype(float) * 3.0
    estimator = fit_linear(train)
    assert isinstance(estimator, LinearRegression)
    prediction = float(estimator.predict(train.loc[:, list(FEATURE_COLUMNS)].to_numpy(dtype=float))[0])
    assert prediction == pytest.approx(0.0, abs=1e-8)


def test_coefficient_frame_puts_the_intercept_first() -> None:
    frame = coefficient_frame(("is_a", "is_b"), 0.5, np.array([1.0, -2.0]))
    assert frame["feature"].tolist() == ["intercept", "is_a", "is_b"]


def test_results_name_the_full_tables() -> None:
    body = render_results(
        train_rows=3,
        test_rows=2,
        train_keep=1,
        train_remove=2,
        test_keep=1,
        test_remove=1,
        shared_posts=2,
        logistic_train=_metric(3, 0.5),
        logistic_test=_metric(2, 0.25),
        linear_train=_linear(3),
        linear_test=_linear(2),
        logistic_coefficients=[("intercept", 0.1), (FEATURE_COLUMNS[0], 0.2)],
        linear_coefficients=[("intercept", -0.1), (FEATURE_COLUMNS[0], -0.2)],
    )
    assert "UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS" in body
    assert "STUDY_2_KEEP_REMOVE_SPLIT_LABELS" in body
    assert "all 2 test posts also appear in training" in body


def _feature_only_frame(rows: int) -> pd.DataFrame:
    frame = pd.DataFrame({"keep_remove_label": [0] * rows, "remove_proportion": [0.2] * rows})
    for column in FEATURE_COLUMNS:
        frame[column] = 0
    frame.loc[0, FEATURE_COLUMNS[0]] = 0
    if rows > 1:
        frame.loc[1, FEATURE_COLUMNS[0]] = 1
    return frame


def _metric(rows: int, accuracy: float) -> dict[str, float]:
    return {
        "sample_count": float(rows),
        "accuracy": accuracy,
        "precision": 0.1,
        "recall": 0.2,
        "f1": 0.3,
        "constant_keep_accuracy": 0.4,
    }


def _linear(rows: int) -> dict[str, float]:
    return {
        "sample_count": float(rows),
        "mae": 0.1,
        "rmse": 0.2,
        "r2": 0.3,
        "outside_count": 0.0,
    }
