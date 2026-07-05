"""Threshold analysis for ModernBERT keep/remove predictions.

Sweeps decision thresholds ``0.1``–``0.9`` and writes per-metric JSON + line
plots under ``outputs/threshold_analysis/<timestamp>/``.

Run from root::

    PYTHONPATH=. uv run --extra modernbert-training python \\
      experiments/predict_keep_remove_2026_07_01/models/modernbert/threshold_analysis.py \\
      --run-dir experiments/predict_keep_remove_2026_07_01/models/modernbert/artifacts/modernbert-base/<timestamp>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt

from experiments.predict_keep_remove_2026_07_01.models.modernbert.evaluate import (
    THRESHOLDS,
    _metrics_for_split,
)
from lib.timestamp_utils import get_current_timestamp

_METRIC_NAMES = ("accuracy", "precision", "recall", "f1")
_OUTPUTS_PARENT = Path(__file__).resolve().parent / "outputs" / "threshold_analysis"


def _summary_for_metric(
    metric: str,
    threshold_metrics: dict[str, dict[str, float]],
) -> dict[str, float | str]:
    values_by_threshold = {
        float(threshold): float(threshold_metrics[threshold][metric])
        for threshold in threshold_metrics
    }
    highest_threshold = max(values_by_threshold, key=values_by_threshold.get)
    return {
        "highest_value": values_by_threshold[highest_threshold],
        "value_at_0.5": values_by_threshold[0.5],
        "threshold_at_highest": f"{highest_threshold:.1f}",
    }


def _plot_metric(
    *,
    metric: str,
    thresholds: list[float],
    values: list[float],
    split: str,
    out_path: Path,
    highest_threshold: float,
    highest_value: float,
) -> None:
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.plot(
        thresholds,
        values,
        marker="o",
        linewidth=2,
        markersize=7,
        color="#1f77b4",
        label=split,
    )
    ax.axvline(0.5, color="gray", linestyle="--", linewidth=1.2, alpha=0.8, label="p = 0.5")
    ax.scatter(
        [highest_threshold],
        [highest_value],
        color="#d62728",
        s=80,
        zorder=5,
        label=f"max ({highest_threshold:.1f})",
    )

    ax.set_xlim(0.05, 0.95)
    ax.set_ylim(0.0, 1.0)
    ax.set_xticks(thresholds)
    ax.set_xlabel("Decision threshold (p)")
    ax.set_ylabel(metric.capitalize())
    ax.set_title(f"ModernBERT {split} {metric.capitalize()} vs threshold")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="best", fontsize=9)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plot ModernBERT threshold curves for accuracy/precision/recall/f1."
    )
    parser.add_argument(
        "--run-dir",
        required=True,
        help="Training run directory containing <split>_predictions.csv.",
    )
    parser.add_argument(
        "--split",
        choices=("val", "test"),
        default="test",
        help="Which prediction CSV to analyze (default: test).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> dict[str, Any]:
    args = parse_args(argv)
    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        raise FileNotFoundError(f"Run dir not found: {run_dir}")

    pred_path = run_dir / f"{args.split}_predictions.csv"
    if not pred_path.is_file():
        raise FileNotFoundError(f"Missing {pred_path}")

    threshold_metrics = _metrics_for_split(pred_path)
    thresholds = [float(t) for t in THRESHOLDS]

    timestamp = get_current_timestamp()
    out_dir = _OUTPUTS_PARENT / timestamp
    out_dir.mkdir(parents=True, exist_ok=False)

    summary_rows: list[dict[str, Any]] = []

    for metric in _METRIC_NAMES:
        values = [float(threshold_metrics[f"{t:.1f}"][metric]) for t in thresholds]
        summary = _summary_for_metric(metric, threshold_metrics)
        highest_threshold = float(summary["threshold_at_highest"])

        payload = {
            "metric": metric,
            "split": args.split,
            "run_dir": str(run_dir.resolve()),
            "predictions_csv": str(pred_path.resolve()),
            "thresholds": thresholds,
            "values": values,
            "summary": summary,
        }
        json_path = out_dir / f"{metric}.json"
        json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

        png_path = out_dir / f"{metric}.png"
        _plot_metric(
            metric=metric,
            thresholds=thresholds,
            values=values,
            split=args.split,
            out_path=png_path,
            highest_threshold=highest_threshold,
            highest_value=float(summary["highest_value"]),
        )

        summary_rows.append(
            {
                "metric": metric,
                "highest_value": summary["highest_value"],
                "value_at_p_0.5": summary["value_at_0.5"],
                "threshold_at_highest": summary["threshold_at_highest"],
            }
        )
        print(f"Wrote {json_path}")
        print(f"Wrote {png_path}")

    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps(
            {
                "timestamp": timestamp,
                "split": args.split,
                "run_dir": str(run_dir.resolve()),
                "rows": summary_rows,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"Wrote {summary_path}")
    print(f"Output directory: {out_dir}")
    return {"output_dir": str(out_dir), "summary_rows": summary_rows}


if __name__ == "__main__":
    main()
