"""XGBoost binary classifier for simplified keep/remove (embedding-driven features)."""

from __future__ import annotations

import pickle
from pathlib import Path
from typing import Any

import numpy as np
from xgboost import XGBClassifier


class XGBoostKeepRemoveModel:
    """Binary classifier on precomputed numeric feature matrices."""

    model_name = "xgboost"

    def __init__(
        self,
        *,
        random_state: int = 42,
        scale_pos_weight: float | None = None,
        n_estimators: int = 300,
        max_depth: int = 6,
        learning_rate: float = 0.05,
        n_jobs: int = -1,
    ) -> None:
        self.random_state = random_state
        self.scale_pos_weight = scale_pos_weight
        self.n_estimators = n_estimators
        self.max_depth = max_depth
        self.learning_rate = learning_rate
        self.n_jobs = n_jobs
        kw: dict[str, Any] = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "learning_rate": learning_rate,
            "subsample": 0.9,
            "colsample_bytree": 0.9,
            "objective": "binary:logistic",
            "eval_metric": "logloss",
            "random_state": random_state,
            "n_jobs": n_jobs,
        }
        if scale_pos_weight is not None:
            kw["scale_pos_weight"] = float(scale_pos_weight)
        self._clf = XGBClassifier(**kw)

    def fit(self, X: np.ndarray, y: np.ndarray) -> XGBoostKeepRemoveModel:
        self._clf.fit(X, y)
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        return self._clf.predict(X)

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self._clf.predict_proba(X)

    def feature_importances(self) -> np.ndarray:
        """Return boosted-tree feature importance vector."""
        return np.asarray(self._clf.feature_importances_, dtype=np.float64)

    def save(self, path: Path | str, *, pickle_protocol: int = pickle.HIGHEST_PROTOCOL) -> None:
        dst = Path(path)
        dst.parent.mkdir(parents=True, exist_ok=True)
        blob: dict[str, Any] = {
            "wrapped": self._clf,
            "hyperparameters": {
                "random_state": self.random_state,
                "scale_pos_weight": self.scale_pos_weight,
                "n_estimators": self.n_estimators,
                "max_depth": self.max_depth,
                "learning_rate": self.learning_rate,
                "n_jobs": self.n_jobs,
            },
            "wrapper": self.model_name,
        }
        dst.write_bytes(pickle.dumps(blob, protocol=pickle_protocol))

    @classmethod
    def load(cls, path: Path | str) -> tuple[XGBoostKeepRemoveModel, dict[str, Any]]:
        blob = pickle.loads(Path(path).read_bytes())
        inner = blob["wrapped"]
        if not isinstance(inner, XGBClassifier):
            raise TypeError(f"Expected XGBClassifier; got {type(inner)!r}")
        hypers = blob.get("hyperparameters", {})
        m = cls(
            random_state=int(hypers.get("random_state", 42)),
            scale_pos_weight=hypers.get("scale_pos_weight"),
            n_estimators=int(hypers.get("n_estimators", 300)),
            max_depth=int(hypers.get("max_depth", 6)),
            learning_rate=float(hypers.get("learning_rate", 0.05)),
            n_jobs=int(hypers.get("n_jobs", -1)),
        )
        m._clf = inner
        return m, blob
