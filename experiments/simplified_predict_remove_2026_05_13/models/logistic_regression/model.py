"""Sklearn logistic regression classifier for simplified keep/remove (embedding-driven features)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
from sklearn.linear_model import LogisticRegression


class LogisticRegressionKeepRemoveModel:
    """Binary classifier on precomputed numeric feature matrices."""

    model_name = "logistic_regression"

    def __init__(
        self,
        *,
        max_iter: int = 2000,
        random_state: int = 42,
        class_weight: str | dict[str, float] | None = None,
    ) -> None:
        self.max_iter = max_iter
        self.random_state = random_state
        self.class_weight = class_weight
        self._clf = LogisticRegression(
            max_iter=max_iter,
            random_state=random_state,
            solver="liblinear",
            class_weight=class_weight,
        )

    def fit(self, X: np.ndarray, y: np.ndarray) -> LogisticRegressionKeepRemoveModel:
        self._clf.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._clf.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        """Return sklearn ``predict_proba``; column index 1 is remove probability."""
        return self._clf.predict_proba(X)

    def classification_coefficients(self) -> np.ndarray:
        """Return shape ``(n_features,)`` learned weights (excluding intercept)."""
        return np.asarray(self._clf.coef_[0], dtype=np.float64)

    def save(self, path: Path | str, *, pickle_protocol: int = pickle.HIGHEST_PROTOCOL) -> None:
        dst = Path(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        blob: dict[str, Any] = {
            "wrapped": self._clf,
            "hyperparameters": {
                "max_iter": self.max_iter,
                "random_state": self.random_state,
                "class_weight": self.class_weight,
            },
            "wrapper": self.model_name,
        }
        dst.write_bytes(pickle.dumps(blob, protocol=pickle_protocol))

    @classmethod
    def load(cls, path: Path | str) -> tuple[LogisticRegressionKeepRemoveModel, dict[str, Any]]:
        blob = pickle.loads(Path(path).read_bytes())
        inner = blob["wrapped"]
        if not isinstance(inner, LogisticRegression):
            raise TypeError(f"Expected LogisticRegression; got {type(inner)!r}")
        hypers = blob.get("hyperparameters", {})
        m = cls(
            max_iter=int(hypers.get("max_iter", 2000)),
            random_state=int(hypers.get("random_state", 42)),
            class_weight=hypers.get("class_weight"),
        )
        m._clf = inner
        return m, blob
