"""Cross-model metric plots for Bedrock zero-shot baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/plot_results.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
import pandas as pd

from experiments.predict_keep_remove_2026_07_01.models.llm_finetuning.api_baselines.constants import (
    VARIANT_BY_SLUG,
)
from lib.timestamp_utils import get_current_timestamp

_METRIC_NAMES = ("accuracy", "precision", "recall", "f1")
_API_BASELINES_ROOT = Path(__file__).resolve().parent
_OUTPUTS_PARENT = _API_BASELINES_ROOT / "outputs" / "plot_results"


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _extract_metrics(metrics: dict[str, Any]) -> dict[str, float]:
    if "metrics" not in metrics:
        raise KeyError("metrics.json missing 'metrics'")
    return metrics["metrics"]


def _latest_run_dir(variant_folder: Path) -> Path | None:
    outputs_dir = variant_folder / "outputs"
    if not outputs_dir.is_dir():
        return None
    candidates = [
        p
        for p in outputs_dir.iterdir()
        if p.is_dir() and (p / "metrics.json").is_file() and (p / "metadata.json").is_file()
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda p: p.name)


def _collect_rows() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for variant in VARIANT_BY_SLUG.values():
        variant_dir = _API_BASELINES_ROOT / variant.folder
        run_dir = _latest_run_dir(variant_dir)
        if run_dir is None:
            continue

        meta = _read_json(run_dir / "metadata.json")
        split_metrics = _extract_metrics(_read_json(run_dir / "metrics.json"))
        model_label = variant.display_name

        rows.append(
            {
                "model": model_label,
                "variant_slug": variant.variant_slug,
                "bedrock_model_id": meta.get("bedrock_model_id", variant.bedrock_model_id),
                "run_dir": str(run_dir),
                "accuracy": float(split_metrics["accuracy"]),
                "precision": float(split_metrics["precision"]),
                "recall": float(split_metrics["recall"]),
                "f1": float(split_metrics["f1"]),
            }
        )
    return rows


def _plot_metric(*, df: pd.DataFrame, metric: str, out_path: Path) -> None:
    models = list(df["model"].drop_duplicates())
    values = [float(df[df["model"] == m][metric].iloc[0]) for m in models]
    x = range(len(models))

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(list(x), values, color="#1f77b4")

    ax.set_xticks(list(x))
    ax.set_xticklabels(models, rotation=20, ha="right")
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel(metric.capitalize())
    ax.set_title(f"Bedrock zero-shot baselines — {metric.capitalize()}")
    ax.grid(True, axis="y", alpha=0.3)

    fig.tight_layout()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main() -> None:
    rows = _collect_rows()
    if not rows:
        print("No completed Bedrock baseline runs found (no metrics.json).")
        return

    df = pd.DataFrame(rows).sort_values(["model"])
    timestamp = get_current_timestamp()
    out_dir = _OUTPUTS_PARENT / timestamp
    out_dir.mkdir(parents=True, exist_ok=True)

    summary = {
        "timestamp": timestamp,
        "models": sorted(df["model"].drop_duplicates().tolist()),
        "rows": rows,
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    for metric in _METRIC_NAMES:
        _plot_metric(df=df, metric=metric, out_path=out_dir / f"{metric}.png")

    print(f"Wrote plot artifacts to {out_dir}")


if __name__ == "__main__":
    main()
