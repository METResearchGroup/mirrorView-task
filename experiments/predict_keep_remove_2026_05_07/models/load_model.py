from __future__ import annotations

from typing import Protocol

import pandas as pd

from experiments.predict_keep_remove_2026_05_07.models.logistic_regression import (
    LogisticRegressionModel,
)
from experiments.predict_keep_remove_2026_05_07.models.xgboost import XGBoostModel


class ModelStrategy(Protocol):
    """Training strategy interface used by the model loader."""

    model_name: str

    def train(
        self,
        train_df: pd.DataFrame,
        test_df: pd.DataFrame,
        *,
        output_dir,
        target_column: str = "keep_remove_label",
    ) -> dict: ...


MODEL_REGISTRY: dict[str, type[ModelStrategy]] = {
    "logistic_regression": LogisticRegressionModel,
    "xgboost": XGBoostModel,
}


def load_model(model_name: str) -> ModelStrategy:
    """Return a model strategy instance for the provided model name."""
    key = model_name.strip().lower()
    model_cls = MODEL_REGISTRY.get(key)
    if model_cls is None:
        available = ", ".join(sorted(MODEL_REGISTRY))
        raise ValueError(f"Unknown model '{model_name}'. Available models: {available}")
    return model_cls()
