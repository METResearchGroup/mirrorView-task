"""Generate scaling curves for the XGBoost keep/remove model.

What it does:
- Loads the linked-fate keep/remove dataset used by other experiments in
  `experiments/predict_keep_remove_2026_05_07/`.
- Re-trains the XGBoost model multiple times, varying the train/test split
  proportion from 10/90 to 90/10 in increments of 10%.
- For each split, reports (on the test set):
  accuracy, precision, recall, F1, ROC-AUC, where precision/recall/F1/ROC-AUC
  treat `remove` as the positive class (label=1).
- Produces a single PNG plot and a `results.json` file under:
  `experiments/predict_keep_remove_2026_05_07/outputs/scaling_curves/{timestamp}/`.

How to run (from repo root):
`PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/generate_scaling_curves.py --seed 42`
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")  # headless PNG generation
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from xgboost import XGBClassifier

from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from experiments.predict_keep_remove_2026_05_07.models.logistic_regression import (
    DEFAULT_FEATURE_COLUMNS,
)
from lib.timestamp_utils import get_current_timestamp


@dataclass(frozen=True)
class SplitMetrics:
    train_split: float
    train_rows: int
    test_rows: int
    accuracy: float
    precision: float
    recall: float
    f1: float
    roc_auc: float


def _featurize_train_like_xgboost(train_df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Match the featurization approach used in XGBoostModel (one-hot + numeric coerce)."""
    X = train_df.loc[:, DEFAULT_FEATURE_COLUMNS].copy()
    X = pd.get_dummies(X, columns=["sample_toxicity_type", "sampled_stance"], dummy_na=False)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0.0)
    encoded_cols = list(X.columns)
    return X, encoded_cols


def _featurize_infer_like_xgboost(test_df: pd.DataFrame, encoded_cols: list[str]) -> pd.DataFrame:
    X = test_df.loc[:, DEFAULT_FEATURE_COLUMNS].copy()
    X = pd.get_dummies(X, columns=["sample_toxicity_type", "sampled_stance"], dummy_na=False)
    X = X.reindex(columns=encoded_cols, fill_value=0.0)
    for col in X.columns:
        X[col] = pd.to_numeric(X[col], errors="coerce")
    X = X.fillna(0.0)
    return X


def _train_and_eval_xgboost(
    *,
    train_df: pd.DataFrame,
    test_df: pd.DataFrame,
    seed: int,
) -> dict[str, float]:
    X_train, encoded_cols = _featurize_train_like_xgboost(train_df)
    X_test = _featurize_infer_like_xgboost(test_df, encoded_cols)

    y_train = train_df["keep_remove_label"].astype(int)
    y_test = test_df["keep_remove_label"].astype(int)

    model = XGBClassifier(
        n_estimators=300,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        objective="binary:logistic",
        eval_metric="logloss",
        random_state=seed,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    y_prob = model.predict_proba(X_test)[:, 1]

    return {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
    }


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42, help="Random seed for splits and XGBoost.")
    parser.add_argument(
        "--train-splits",
        type=float,
        nargs="*",
        default=None,
        help="Optional list of train split fractions (e.g. 0.1 0.2 ... 0.9).",
    )
    args = parser.parse_args()

    train_splits = args.train_splits
    if not train_splits:
        train_splits = [0.1 * i for i in range(1, 10)]
    # Deterministic order
    train_splits = sorted(float(s) for s in train_splits)

    timestamp = get_current_timestamp()
    output_dir = (
        Path(__file__).resolve().parent
        / "outputs"
        / "scaling_curves"
        / timestamp
    )
    output_dir.mkdir(parents=True, exist_ok=False)

    dataloader = Dataloader()
    full_df = dataloader.load_training_dataframe()

    results: list[SplitMetrics] = []
    for train_split in train_splits:
        # Match Dataloader.generate_train_test_split logic: shuffle then take prefix.
        shuffled = full_df.sample(frac=1.0, random_state=args.seed).reset_index(drop=True)
        train_count = int(len(shuffled) * train_split)
        train_df = shuffled.iloc[:train_count].copy()
        test_df = shuffled.iloc[train_count:].copy()

        metrics = _train_and_eval_xgboost(train_df=train_df, test_df=test_df, seed=args.seed)
        results.append(
            SplitMetrics(
                train_split=train_split,
                train_rows=int(len(train_df)),
                test_rows=int(len(test_df)),
                accuracy=metrics["accuracy"],
                precision=metrics["precision"],
                recall=metrics["recall"],
                f1=metrics["f1"],
                roc_auc=metrics["roc_auc"],
            )
        )

    results_payload: dict[str, Any] = {
        "timestamp": timestamp,
        "seed": args.seed,
        "model": {
            "name": "xgboost",
            "hyperparameters": {
                "n_estimators": 300,
                "max_depth": 6,
                "learning_rate": 0.05,
                "subsample": 0.9,
                "colsample_bytree": 0.9,
                "objective": "binary:logistic",
                "eval_metric": "logloss",
            },
        },
        "target": {"column": "keep_remove_label", "positive_class": {"value": 1, "meaning": "remove"}},
        "splits": [asdict(r) for r in results],
    }

    (output_dir / "results.json").write_text(json.dumps(results_payload, indent=2), encoding="utf-8")

    # Plot
    xs = [r.train_split for r in results]
    to_y = lambda key: [float(getattr(r, key)) for r in results]

    plt.figure(figsize=(10, 6))
    plt.plot(xs, to_y("accuracy"), marker="o", label="Accuracy")
    plt.plot(xs, to_y("precision"), marker="o", label="Precision (remove=1)")
    plt.plot(xs, to_y("recall"), marker="o", label="Recall (remove=1)")
    plt.plot(xs, to_y("f1"), marker="o", label="F1 (remove=1)")
    plt.plot(xs, to_y("roc_auc"), marker="o", label="ROC-AUC (remove=1)")
    plt.xlabel("Train split fraction")
    plt.ylabel("Metric value")
    plt.title("XGBoost scaling curves: train/test size vs remove prediction metrics")
    plt.ylim(0.0, 1.05)
    plt.grid(True, alpha=0.3)
    plt.legend()

    results_png_path = output_dir / "results.png"
    plt.tight_layout()
    plt.savefig(results_png_path, dpi=200)

    print(f"Saved: {results_png_path}")
    print(f"Saved: {output_dir / 'results.json'}")


if __name__ == "__main__":
    main()

