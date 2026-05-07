"""Run remove-focused calibration and threshold selection for keep/remove models.

Purpose:
- Build a 3-way split (train/calibration/test) from linked-fate keep/remove rows.
- Fit a base classifier (logistic regression or XGBoost).
- Calibrate remove probabilities (sigmoid/Platt-style or isotonic).
- Select a decision threshold using a remove-focused policy.
- Save metrics, predictions, and visualization artifacts under timestamped outputs.

How to run:
- Default run:
  PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/calibration/run_calibration.py
- Example explicit options:
  PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/calibration/run_calibration.py --model xgboost --calibrator sigmoid --threshold-policy max_f1_remove --seed 42
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import typer
from sklearn.calibration import calibration_curve
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    average_precision_score,
    balanced_accuracy_score,
    brier_score_loss,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier

from experiments.predict_keep_remove_2026_05_07.dataloader import Dataloader
from experiments.predict_keep_remove_2026_05_07.models.logistic_regression import (
    LogisticRegressionModel,
)
from experiments.predict_keep_remove_2026_05_07.models.xgboost import XGBoostModel
from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)


@dataclass
class CalibrationMetrics:
    brier_score: float
    ece: float
    bin_table: pd.DataFrame


def _fit_base_model(model_name: str, train_df: pd.DataFrame, seed: int) -> tuple[Any, Any]:
    """Fit base model and return (model_strategy, fitted_estimator)."""
    key = model_name.strip().lower()
    if key == "logistic_regression":
        strategy = LogisticRegressionModel(random_state=seed)
        x_train = strategy._featurize_train(train_df)
        y_train = train_df[Dataloader.TARGET_COLUMN].astype(int)
        estimator = LogisticRegression(
            max_iter=strategy.max_iter,
            random_state=seed,
            solver="liblinear",
        )
        estimator.fit(x_train, y_train)
        return strategy, estimator

    if key == "xgboost":
        strategy = XGBoostModel(random_state=seed)
        x_train = strategy._featurize_train(train_df)
        y_train = train_df[Dataloader.TARGET_COLUMN].astype(int)
        estimator = XGBClassifier(
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
        estimator.fit(x_train, y_train)
        return strategy, estimator

    raise ValueError("Unsupported model. Use 'logistic_regression' or 'xgboost'.")


def _predict_remove_probability(strategy: Any, estimator: Any, df: pd.DataFrame) -> np.ndarray:
    x = strategy._featurize_infer(df)
    return estimator.predict_proba(x)[:, 1]


def _compute_ece_and_bins(
    y_true: np.ndarray, y_prob: np.ndarray, n_bins: int = 10
) -> CalibrationMetrics:
    bins = np.linspace(0.0, 1.0, n_bins + 1)
    bin_ids = np.digitize(y_prob, bins, right=True)
    rows: list[dict[str, float | int]] = []
    weighted_abs_error = 0.0
    total = max(len(y_true), 1)

    for idx in range(1, n_bins + 1):
        mask = bin_ids == idx
        count = int(mask.sum())
        if count == 0:
            rows.append(
                {
                    "bin_idx": idx,
                    "bin_start": float(bins[idx - 1]),
                    "bin_end": float(bins[idx]),
                    "count": 0,
                    "avg_predicted_prob": float("nan"),
                    "empirical_positive_rate": float("nan"),
                    "abs_gap": float("nan"),
                }
            )
            continue

        pred_mean = float(np.mean(y_prob[mask]))
        true_mean = float(np.mean(y_true[mask]))
        abs_gap = abs(pred_mean - true_mean)
        weighted_abs_error += (count / total) * abs_gap
        rows.append(
            {
                "bin_idx": idx,
                "bin_start": float(bins[idx - 1]),
                "bin_end": float(bins[idx]),
                "count": count,
                "avg_predicted_prob": pred_mean,
                "empirical_positive_rate": true_mean,
                "abs_gap": abs_gap,
            }
        )

    return CalibrationMetrics(
        brier_score=float(brier_score_loss(y_true, y_prob)),
        ece=float(weighted_abs_error),
        bin_table=pd.DataFrame(rows),
    )


def _threshold_sweep(
    y_true: np.ndarray,
    y_prob: np.ndarray,
    start: float = 0.05,
    end: float = 0.95,
    step: float = 0.01,
) -> pd.DataFrame:
    thresholds = np.arange(start, end + 1e-9, step)
    rows: list[dict[str, float | int]] = []
    for threshold in thresholds:
        y_pred = (y_prob >= threshold).astype(int)
        tp = int(np.sum((y_true == 1) & (y_pred == 1)))
        fp = int(np.sum((y_true == 0) & (y_pred == 1)))
        tn = int(np.sum((y_true == 0) & (y_pred == 0)))
        fn = int(np.sum((y_true == 1) & (y_pred == 0)))
        rows.append(
            {
                "threshold": float(threshold),
                "accuracy": float(accuracy_score(y_true, y_pred)),
                "precision_remove": float(precision_score(y_true, y_pred, zero_division=0)),
                "recall_remove": float(recall_score(y_true, y_pred, zero_division=0)),
                "f1_remove": float(f1_score(y_true, y_pred, zero_division=0)),
                "balanced_accuracy": float(
                    balanced_accuracy_score(y_true, y_pred)
                ),
                "tp": tp,
                "fp": fp,
                "tn": tn,
                "fn": fn,
            }
        )
    return pd.DataFrame(rows)


def _select_threshold(
    sweep_df: pd.DataFrame, policy: str, recall_target: float
) -> tuple[float, dict[str, float]]:
    if policy == "max_f1_remove":
        best_row = sweep_df.sort_values(["f1_remove", "threshold"], ascending=[False, True]).iloc[0]
    elif policy == "max_precision_with_recall_constraint":
        valid = sweep_df[sweep_df["recall_remove"] >= recall_target].copy()
        if valid.empty:
            best_row = sweep_df.sort_values(
                ["recall_remove", "precision_remove", "threshold"],
                ascending=[False, False, True],
            ).iloc[0]
        else:
            best_row = valid.sort_values(
                ["precision_remove", "recall_remove", "threshold"],
                ascending=[False, False, True],
            ).iloc[0]
    else:
        raise ValueError(
            "Unknown policy. Use 'max_f1_remove' or 'max_precision_with_recall_constraint'."
        )

    threshold = float(best_row["threshold"])
    metrics = {
        "accuracy": float(best_row["accuracy"]),
        "precision_remove": float(best_row["precision_remove"]),
        "recall_remove": float(best_row["recall_remove"]),
        "f1_remove": float(best_row["f1_remove"]),
        "balanced_accuracy": float(best_row["balanced_accuracy"]),
    }
    return threshold, metrics


def _evaluate_at_threshold(y_true: np.ndarray, y_prob: np.ndarray, threshold: float) -> dict[str, float]:
    y_pred = (y_prob >= threshold).astype(int)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision_remove": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall_remove": float(recall_score(y_true, y_pred, zero_division=0)),
        "f1_remove": float(f1_score(y_true, y_pred, zero_division=0)),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
        "roc_auc_remove": float(roc_auc_score(y_true, y_prob)),
        "pr_auc_remove": float(average_precision_score(y_true, y_prob)),
    }


def _plot_reliability(y_true: np.ndarray, p_raw: np.ndarray, p_cal: np.ndarray, path: Path) -> None:
    plt.figure(figsize=(7, 6))
    frac_raw, mean_raw = calibration_curve(y_true, p_raw, n_bins=10, strategy="uniform")
    frac_cal, mean_cal = calibration_curve(y_true, p_cal, n_bins=10, strategy="uniform")
    plt.plot([0, 1], [0, 1], "--", color="gray", label="Perfect calibration")
    plt.plot(mean_raw, frac_raw, marker="o", label="Raw")
    plt.plot(mean_cal, frac_cal, marker="o", label="Calibrated")
    plt.xlabel("Predicted remove probability")
    plt.ylabel("Empirical remove frequency")
    plt.title("Reliability Curve (Calibration Split)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_threshold_sweep(sweep_df: pd.DataFrame, selected_threshold: float, path: Path) -> None:
    plt.figure(figsize=(9, 6))
    plt.plot(sweep_df["threshold"], sweep_df["f1_remove"], label="F1 remove")
    plt.plot(sweep_df["threshold"], sweep_df["precision_remove"], label="Precision remove")
    plt.plot(sweep_df["threshold"], sweep_df["recall_remove"], label="Recall remove")
    plt.plot(sweep_df["threshold"], sweep_df["balanced_accuracy"], label="Balanced accuracy")
    plt.axvline(selected_threshold, color="black", linestyle="--", label=f"Selected t={selected_threshold:.2f}")
    plt.xlabel("Threshold")
    plt.ylabel("Metric value")
    plt.title("Threshold Sweep (Calibration Split)")
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=160)
    plt.close()


def _plot_calibration_metrics_over_time(current_outputs_dir: Path, current_run_dir: Path) -> None:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(current_outputs_dir.glob("*")):
        metrics_path = run_dir / "calibration_metrics.json"
        metadata_path = run_dir / "metadata.json"
        if not metrics_path.exists() or not metadata_path.exists():
            continue
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        rows.append(
            {
                "timestamp": metadata.get("timestamp", run_dir.name),
                "brier_raw": metrics["raw"]["brier_score"],
                "brier_calibrated": metrics["calibrated"]["brier_score"],
                "ece_raw": metrics["raw"]["ece"],
                "ece_calibrated": metrics["calibrated"]["ece"],
            }
        )

    if not rows:
        return

    df = pd.DataFrame(rows).sort_values("timestamp")
    plt.figure(figsize=(10, 6))
    x = np.arange(len(df))
    plt.plot(x, df["brier_raw"], marker="o", label="Brier raw")
    plt.plot(x, df["brier_calibrated"], marker="o", label="Brier calibrated")
    plt.plot(x, df["ece_raw"], marker="o", label="ECE raw")
    plt.plot(x, df["ece_calibrated"], marker="o", label="ECE calibrated")
    plt.xticks(x, df["timestamp"], rotation=45, ha="right")
    plt.xlabel("Run timestamp")
    plt.ylabel("Score (lower is better)")
    plt.title("Calibration Metrics Over Time")
    plt.legend()
    plt.tight_layout()
    plt.savefig(current_run_dir / "calibration_metrics_over_time.png", dpi=160)
    plt.close()


@app.command()
def run(
    model: str = typer.Option(
        "xgboost",
        "--model",
        help="Base model to calibrate: logistic_regression or xgboost.",
    ),
    calibrator: str = typer.Option(
        "sigmoid",
        "--calibrator",
        help="Calibration method: sigmoid or isotonic.",
    ),
    threshold_policy: str = typer.Option(
        "max_f1_remove",
        "--threshold-policy",
        help="Threshold policy: max_f1_remove or max_precision_with_recall_constraint.",
    ),
    recall_target: float = typer.Option(
        0.80,
        "--recall-target",
        help="Recall target used for constraint policy.",
    ),
    train_fraction: float = typer.Option(0.64, "--train-fraction", min=0.05, max=0.95),
    calibration_fraction: float = typer.Option(0.16, "--calibration-fraction", min=0.05, max=0.95),
    seed: int = typer.Option(42, "--seed"),
) -> None:
    """Run calibration + threshold selection and write all artifacts."""
    if train_fraction + calibration_fraction >= 1.0:
        raise ValueError("train_fraction + calibration_fraction must be < 1.0")

    dataloader = Dataloader()
    df = dataloader.load_training_dataframe().copy()
    y = df[Dataloader.TARGET_COLUMN].astype(int)

    train_df, temp_df = train_test_split(
        df,
        train_size=train_fraction,
        random_state=seed,
        stratify=y,
    )
    remaining_fraction = 1.0 - train_fraction
    calibration_size_within_temp = calibration_fraction / remaining_fraction
    cal_df, test_df = train_test_split(
        temp_df,
        train_size=calibration_size_within_temp,
        random_state=seed,
        stratify=temp_df[Dataloader.TARGET_COLUMN].astype(int),
    )

    strategy, estimator = _fit_base_model(model, train_df, seed)
    y_cal = cal_df[Dataloader.TARGET_COLUMN].astype(int).to_numpy()
    y_test = test_df[Dataloader.TARGET_COLUMN].astype(int).to_numpy()

    p_remove_cal_raw = _predict_remove_probability(strategy, estimator, cal_df)
    p_remove_test_raw = _predict_remove_probability(strategy, estimator, test_df)

    if calibrator == "sigmoid":
        cal_model = LogisticRegression(solver="lbfgs")
        cal_model.fit(p_remove_cal_raw.reshape(-1, 1), y_cal)
        p_remove_cal_calibrated = cal_model.predict_proba(p_remove_cal_raw.reshape(-1, 1))[:, 1]
        p_remove_test_calibrated = cal_model.predict_proba(p_remove_test_raw.reshape(-1, 1))[:, 1]
    elif calibrator == "isotonic":
        cal_model = IsotonicRegression(out_of_bounds="clip")
        cal_model.fit(p_remove_cal_raw, y_cal)
        p_remove_cal_calibrated = cal_model.predict(p_remove_cal_raw)
        p_remove_test_calibrated = cal_model.predict(p_remove_test_raw)
    else:
        raise ValueError("Unknown calibrator. Use 'sigmoid' or 'isotonic'.")

    raw_metrics = _compute_ece_and_bins(y_cal, p_remove_cal_raw)
    calibrated_metrics = _compute_ece_and_bins(y_cal, p_remove_cal_calibrated)

    threshold_sweep = _threshold_sweep(y_cal, p_remove_cal_calibrated)
    selected_threshold, selected_validation_metrics = _select_threshold(
        threshold_sweep, threshold_policy, recall_target
    )
    test_metrics = _evaluate_at_threshold(y_test, p_remove_test_calibrated, selected_threshold)

    timestamp = get_current_timestamp()
    output_root = Path(__file__).resolve().parent / "outputs"
    output_dir = output_root / timestamp
    output_dir.mkdir(parents=True, exist_ok=False)

    metadata = {
        "timestamp": timestamp,
        "model": model,
        "calibrator": calibrator,
        "threshold_policy": threshold_policy,
        "recall_target": recall_target,
        "seed": seed,
        "train_fraction": train_fraction,
        "calibration_fraction": calibration_fraction,
        "test_fraction": 1.0 - train_fraction - calibration_fraction,
        "row_counts": {
            "train": int(len(train_df)),
            "calibration": int(len(cal_df)),
            "test": int(len(test_df)),
        },
    }
    (output_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    calibration_metrics = {
        "raw": {
            "brier_score": raw_metrics.brier_score,
            "ece": raw_metrics.ece,
        },
        "calibrated": {
            "brier_score": calibrated_metrics.brier_score,
            "ece": calibrated_metrics.ece,
        },
    }
    (output_dir / "calibration_metrics.json").write_text(
        json.dumps(calibration_metrics, indent=2), encoding="utf-8"
    )

    raw_metrics.bin_table.to_csv(output_dir / "calibration_bins_raw.csv", index=False)
    calibrated_metrics.bin_table.to_csv(output_dir / "calibration_bins_calibrated.csv", index=False)
    threshold_sweep.to_csv(output_dir / "threshold_sweep.csv", index=False)

    selected_threshold_payload = {
        "policy": threshold_policy,
        "selected_threshold": selected_threshold,
        "validation_metrics": selected_validation_metrics,
    }
    (output_dir / "selected_threshold.json").write_text(
        json.dumps(selected_threshold_payload, indent=2), encoding="utf-8"
    )
    (output_dir / "test_metrics_at_selected_threshold.json").write_text(
        json.dumps(test_metrics, indent=2), encoding="utf-8"
    )

    test_predictions = test_df[["post_id", Dataloader.TARGET_COLUMN]].copy()
    test_predictions["p_remove_raw"] = p_remove_test_raw
    test_predictions["p_remove_calibrated"] = p_remove_test_calibrated
    test_predictions["predicted_remove_at_threshold"] = (
        p_remove_test_calibrated >= selected_threshold
    ).astype(int)
    test_predictions.to_csv(output_dir / "calibrated_test_predictions.csv", index=False)

    _plot_reliability(y_cal, p_remove_cal_raw, p_remove_cal_calibrated, output_dir / "reliability_curve.png")
    _plot_threshold_sweep(threshold_sweep, selected_threshold, output_dir / "threshold_sweep_curve.png")
    _plot_calibration_metrics_over_time(output_root, output_dir)

    print(f"Output directory: {output_dir}")
    print(f"Selected threshold: {selected_threshold:.4f}")
    print("Validation metrics at selected threshold:")
    for k, v in selected_validation_metrics.items():
        print(f"  - {k}: {v:.6f}")
    print("Test metrics at selected threshold:")
    for k, v in test_metrics.items():
        print(f"  - {k}: {v:.6f}")
    print("Calibration quality (calibration split):")
    print(f"  - raw_brier: {raw_metrics.brier_score:.6f}")
    print(f"  - calibrated_brier: {calibrated_metrics.brier_score:.6f}")
    print(f"  - raw_ece: {raw_metrics.ece:.6f}")
    print(f"  - calibrated_ece: {calibrated_metrics.ece:.6f}")


if __name__ == "__main__":
    app()
