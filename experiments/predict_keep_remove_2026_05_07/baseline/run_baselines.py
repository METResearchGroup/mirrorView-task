from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import typer
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _binary_metrics(y_true: pd.Series, y_pred: pd.Series, *, pos_label: int) -> dict[str, float]:
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true,
        y_pred,
        pos_label=pos_label,
        average="binary",
        zero_division=0,
    )
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
    }


def _class_balance(y: pd.Series) -> dict[str, float]:
    y_int = y.astype(int)
    remove_count = int((y_int == 1).sum())
    keep_count = int((y_int == 0).sum())
    n = int(len(y_int))
    return {
        "n": n,
        "keep_count": keep_count,
        "remove_count": remove_count,
        "keep_rate": float(keep_count / n) if n else float("nan"),
        "remove_rate": float(remove_count / n) if n else float("nan"),
    }


def _evaluate_baseline(
    y_true: pd.Series,
    y_pred: pd.Series,
    y_prob_remove: pd.Series,
) -> dict[str, object]:
    remove_metrics = _binary_metrics(y_true, y_pred, pos_label=1)
    keep_metrics = _binary_metrics(y_true, y_pred, pos_label=0)
    return {
        "remove_as_positive": remove_metrics,
        "keep_as_positive": keep_metrics,
        "roc_auc_remove": float(roc_auc_score(y_true.astype(int), y_prob_remove.astype(float))),
    }


@app.command()
def run(
    train_split: float = typer.Option(
        0.8,
        "--train-split",
        min=0.01,
        max=0.99,
        help="Train-set fraction for train/test split.",
    ),
    seed: int = typer.Option(
        42,
        "--seed",
        help="Random seed for reproducibility.",
    ),
) -> None:
    timestamp = get_current_timestamp()
    output_dir = Path(__file__).resolve().parent / "outputs" / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)

    dataloader = Dataloader()
    full_df = dataloader.load_training_dataframe()
    train_df, test_df = dataloader.generate_train_test_split(train_split=train_split, random_state=seed)

    y_train = train_df[Dataloader.TARGET_COLUMN].astype(int)
    y_test = test_df[Dataloader.TARGET_COLUMN].astype(int)

    class_balance = {
        "overall": _class_balance(full_df[Dataloader.TARGET_COLUMN]),
        "train": _class_balance(y_train),
        "test": _class_balance(y_test),
    }

    prior_remove = float(y_train.mean())
    rng = np.random.default_rng(seed)

    pred_majority_remove = pd.Series(np.ones(len(y_test), dtype=int), index=test_df.index)
    prob_majority_remove = pd.Series(np.ones(len(y_test), dtype=float), index=test_df.index)

    pred_majority_keep = pd.Series(np.zeros(len(y_test), dtype=int), index=test_df.index)
    prob_majority_keep = pd.Series(np.zeros(len(y_test), dtype=float), index=test_df.index)

    random_remove_prob = pd.Series(np.full(len(y_test), prior_remove, dtype=float), index=test_df.index)
    pred_stratified_random = pd.Series(
        (rng.random(len(y_test)) < prior_remove).astype(int),
        index=test_df.index,
    )

    results = {
        "majority_remove": _evaluate_baseline(y_test, pred_majority_remove, prob_majority_remove),
        "majority_keep": _evaluate_baseline(y_test, pred_majority_keep, prob_majority_keep),
        "stratified_random": _evaluate_baseline(y_test, pred_stratified_random, random_remove_prob),
    }

    (output_dir / "class_balance.json").write_text(
        json.dumps(class_balance, indent=2),
        encoding="utf-8",
    )
    (output_dir / "baseline_metrics.json").write_text(
        json.dumps(results, indent=2),
        encoding="utf-8",
    )

    def _save_predictions(name: str, pred: pd.Series, prob_remove: pd.Series) -> None:
        pred_df = test_df[["post_id", "decision", Dataloader.TARGET_COLUMN]].copy()
        pred_df["predicted_label"] = pred.astype(int).values
        pred_df["predicted_remove_probability"] = prob_remove.astype(float).values
        pred_df.to_csv(output_dir / f"test_predictions_{name}.csv", index=False)

    _save_predictions("majority_keep", pred_majority_keep, prob_majority_keep)
    _save_predictions("majority_remove", pred_majority_remove, prob_majority_remove)
    _save_predictions("stratified_random", pred_stratified_random, random_remove_prob)

    metadata = {
        "timestamp": timestamp,
        "train_split": train_split,
        "seed": seed,
        "target_column": Dataloader.TARGET_COLUMN,
        "train_rows": int(len(train_df)),
        "test_rows": int(len(test_df)),
        "prior_remove_from_train": prior_remove,
        "output_dir": str(output_dir),
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    print(f"Output directory: {output_dir}")
    print("Class balance:")
    print(json.dumps(class_balance, indent=2))
    print("Baseline metrics (remove_as_positive f1):")
    for baseline_name, metrics in results.items():
        print(
            f"  - {baseline_name}: "
            f"{metrics['remove_as_positive']['f1']:.6f}"
        )


if __name__ == "__main__":
    app()
