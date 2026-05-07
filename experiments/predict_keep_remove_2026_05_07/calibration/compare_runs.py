"""Aggregate and compare calibration runs across timestamped outputs.

Purpose:
- Read completed calibration run artifacts from calibration outputs.
- Produce a consolidated run-level comparison table and ranking.
- Generate a combined figure for calibration quality and test performance.
- Save comparison artifacts under outputs/_comparisons/{timestamp}/.

How to run:
- Default outputs directory:
  PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/calibration/compare_runs.py
- Custom outputs directory:
  PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_05_07/calibration/compare_runs.py --outputs-dir experiments/predict_keep_remove_2026_05_07/calibration/outputs
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import typer

from lib.timestamp_utils import get_current_timestamp

app = typer.Typer(add_completion=False, no_args_is_help=True)


def _safe_read_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _collect_runs(outputs_dir: Path) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for run_dir in sorted(outputs_dir.glob("*")):
        if not run_dir.is_dir():
            continue

        metadata = _safe_read_json(run_dir / "metadata.json")
        cal_metrics = _safe_read_json(run_dir / "calibration_metrics.json")
        selected_threshold = _safe_read_json(run_dir / "selected_threshold.json")
        test_metrics = _safe_read_json(run_dir / "test_metrics_at_selected_threshold.json")

        if not metadata or not cal_metrics or not selected_threshold or not test_metrics:
            continue

        row: dict[str, Any] = {
            "run_timestamp": metadata.get("timestamp", run_dir.name),
            "run_dir": str(run_dir),
            "model": metadata.get("model"),
            "calibrator": metadata.get("calibrator"),
            "threshold_policy": metadata.get("threshold_policy"),
            "seed": metadata.get("seed"),
            "selected_threshold": selected_threshold.get("selected_threshold"),
            "calibration_raw_brier": cal_metrics["raw"]["brier_score"],
            "calibration_calibrated_brier": cal_metrics["calibrated"]["brier_score"],
            "calibration_raw_ece": cal_metrics["raw"]["ece"],
            "calibration_calibrated_ece": cal_metrics["calibrated"]["ece"],
            "test_accuracy": test_metrics.get("accuracy"),
            "test_precision_remove": test_metrics.get("precision_remove"),
            "test_recall_remove": test_metrics.get("recall_remove"),
            "test_f1_remove": test_metrics.get("f1_remove"),
            "test_balanced_accuracy": test_metrics.get("balanced_accuracy"),
            "test_roc_auc_remove": test_metrics.get("roc_auc_remove"),
            "test_pr_auc_remove": test_metrics.get("pr_auc_remove"),
        }
        rows.append(row)

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows).sort_values("run_timestamp").reset_index(drop=True)
    df["delta_brier"] = df["calibration_raw_brier"] - df["calibration_calibrated_brier"]
    df["delta_ece"] = df["calibration_raw_ece"] - df["calibration_calibrated_ece"]
    return df


def _save_summary(df: pd.DataFrame, summary_dir: Path) -> tuple[Path, Path, Path]:
    summary_dir.mkdir(parents=True, exist_ok=True)
    csv_path = summary_dir / "run_comparison.csv"
    json_path = summary_dir / "run_comparison.json"
    ranking_path = summary_dir / "ranking_by_test_f1.csv"

    df.to_csv(csv_path, index=False)
    json_path.write_text(
        json.dumps(df.to_dict(orient="records"), indent=2),
        encoding="utf-8",
    )

    ranking = df.sort_values(
        ["test_f1_remove", "test_pr_auc_remove", "test_recall_remove"],
        ascending=[False, False, False],
    )
    ranking.to_csv(ranking_path, index=False)
    return csv_path, json_path, ranking_path


def _plot_compare(df: pd.DataFrame, out_path: Path) -> None:
    labels = [f'{r["run_timestamp"]}\n{r["calibrator"]}' for _, r in df.iterrows()]
    x = np.arange(len(df))
    width = 0.22

    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    axes[0].bar(x - width, df["calibration_raw_brier"], width=width, label="Raw Brier")
    axes[0].bar(
        x,
        df["calibration_calibrated_brier"],
        width=width,
        label="Calibrated Brier",
    )
    axes[0].bar(x + width, df["calibration_calibrated_ece"], width=width, label="Calibrated ECE")
    axes[0].set_title("Calibration Quality by Run (Lower is Better)")
    axes[0].set_ylabel("Score")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(labels, rotation=30, ha="right")
    axes[0].legend()

    axes[1].plot(x, df["test_f1_remove"], marker="o", label="Test F1 remove")
    axes[1].plot(x, df["test_precision_remove"], marker="o", label="Test precision remove")
    axes[1].plot(x, df["test_recall_remove"], marker="o", label="Test recall remove")
    axes[1].plot(x, df["test_pr_auc_remove"], marker="o", label="Test PR-AUC remove")
    axes[1].set_title("Test Performance by Run (Higher is Better)")
    axes[1].set_ylabel("Metric value")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(labels, rotation=30, ha="right")
    axes[1].legend()

    fig.tight_layout()
    fig.savefig(out_path, dpi=170)
    plt.close(fig)


@app.command()
def run(
    outputs_dir: Path = typer.Option(
        Path(__file__).resolve().parent / "outputs",
        "--outputs-dir",
        help="Directory that contains timestamped calibration run outputs.",
    ),
) -> None:
    """Aggregate calibration runs into a single comparison summary + visualization."""
    df = _collect_runs(outputs_dir)
    if df.empty:
        raise RuntimeError(f"No complete calibration runs found in: {outputs_dir}")

    summary_timestamp = get_current_timestamp()
    summary_dir = outputs_dir / "_comparisons" / summary_timestamp
    csv_path, json_path, ranking_path = _save_summary(df, summary_dir)
    plot_path = summary_dir / "run_comparison.png"
    _plot_compare(df, plot_path)

    top = df.sort_values(
        ["test_f1_remove", "test_pr_auc_remove", "test_recall_remove"],
        ascending=[False, False, False],
    ).iloc[0]

    print(f"Summary directory: {summary_dir}")
    print(f"Comparison CSV: {csv_path}")
    print(f"Comparison JSON: {json_path}")
    print(f"Ranking CSV: {ranking_path}")
    print(f"Comparison plot: {plot_path}")
    print("Top run by remove-focused ranking:")
    print(f'  - run_timestamp: {top["run_timestamp"]}')
    print(f'  - calibrator: {top["calibrator"]}')
    print(f'  - threshold: {top["selected_threshold"]:.4f}')
    print(f'  - test_f1_remove: {top["test_f1_remove"]:.6f}')
    print(f'  - test_precision_remove: {top["test_precision_remove"]:.6f}')
    print(f'  - test_recall_remove: {top["test_recall_remove"]:.6f}')
    print(f'  - test_pr_auc_remove: {top["test_pr_auc_remove"]:.6f}')


if __name__ == "__main__":
    app()
