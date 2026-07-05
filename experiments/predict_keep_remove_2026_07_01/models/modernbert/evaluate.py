"""Threshold calibration for a ModernBERT training run.

Sweeps decision thresholds ``0.1``–``0.9`` (step ``0.1``) on val and test
prediction CSVs and writes ``calibration.json`` into the run directory.

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python \\
      experiments/predict_keep_remove_2026_07_01/models/modernbert/evaluate.py \\
      --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

THRESHOLDS = [round(x * 0.1, 1) for x in range(1, 10)]


def _classification_metrics_summary(
    y_true: Any,
    y_pred: Any,
    pos_scores: Any,
) -> dict[str, float]:
    try:
        from experiments.simplified_predict_remove_2026_05_13.features import (
            classification_metrics_summary,
        )

        return classification_metrics_summary(y_true, y_pred, pos_scores)
    except ImportError:
        from sklearn.metrics import (
            accuracy_score,
            average_precision_score,
            confusion_matrix,
            f1_score,
            precision_score,
            recall_score,
            roc_auc_score,
        )

        y_t = np.asarray(y_true).astype(np.int64)
        y_p = np.asarray(y_pred).astype(np.int64)
        s = np.asarray(pos_scores).astype(np.float64)
        out: dict[str, float] = {
            "accuracy": float(accuracy_score(y_t, y_p)),
            "precision": float(precision_score(y_t, y_p, zero_division=0)),
            "recall": float(recall_score(y_t, y_p, zero_division=0)),
            "f1": float(f1_score(y_t, y_p, zero_division=0)),
        }

        def _maybe(fn: Any) -> float:
            try:
                return float(fn())
            except ValueError:
                return float("nan")

        out["roc_auc"] = _maybe(lambda: roc_auc_score(y_t, s))
        out["pr_auc"] = _maybe(lambda: average_precision_score(y_t, s))
        cm = confusion_matrix(y_t, y_p, labels=[0, 1])
        tn, fp, fn, tp = cm.ravel().tolist()
        out["confusion_matrix_tn"] = float(tn)
        out["confusion_matrix_fp"] = float(fp)
        out["confusion_matrix_fn"] = float(fn)
        out["confusion_matrix_tp"] = float(tp)
        return out


def _metrics_for_split(pred_path: Path) -> dict[str, dict[str, float]]:
    df = pd.read_csv(pred_path)
    required = {"keep_remove_label", "predicted_remove_probability"}
    missing = required - set(df.columns)
    if missing:
        raise KeyError(f"{pred_path} missing columns: {sorted(missing)}")

    y_true = df["keep_remove_label"].astype(int).to_numpy()
    proba = df["predicted_remove_probability"].astype(float).to_numpy()

    out: dict[str, dict[str, float]] = {}
    for threshold in THRESHOLDS:
        y_pred = (proba >= threshold).astype(int)
        metrics = _classification_metrics_summary(y_true, y_pred, proba)
        # Calibration contract: accuracy/precision/recall/f1 (plus extras ok).
        out[f"{threshold:.1f}"] = {
            "accuracy": metrics["accuracy"],
            "precision": metrics["precision"],
            "recall": metrics["recall"],
            "f1": metrics["f1"],
        }
    return out


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Calibrate ModernBERT keep/remove thresholds on a run dir."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Training run directory containing val/test prediction CSVs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run dir not found: {run_dir}")

    val_path = run_dir / "val_predictions.csv"
    test_path = run_dir / "test_predictions.csv"
    if not val_path.is_file():
        raise FileNotFoundError(f"Missing {val_path}")
    if not test_path.is_file():
        raise FileNotFoundError(f"Missing {test_path}")

    calibration = {
        "val": _metrics_for_split(val_path),
        "test": _metrics_for_split(test_path),
    }
    out_path = run_dir / "calibration.json"
    out_path.write_text(json.dumps(calibration, indent=2), encoding="utf-8")
    print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
