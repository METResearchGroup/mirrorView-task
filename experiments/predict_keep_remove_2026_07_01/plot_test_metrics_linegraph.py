from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from lib.timestamp_utils import get_current_timestamp


METRIC_ORDER = ["Accuracy", "Precision", "Recall", "F1"]


@dataclass(frozen=True)
class SeriesPoint:
    metric: str
    value: float


@dataclass(frozen=True)
class PlotSeries:
    # e.g. "Logistic regression (feature engineering)"
    label: str
    # e.g. "Logistic regression"
    model_class: str
    training_type: str
    linestyle: str
    color: str
    points: tuple[SeriesPoint, ...]

    def y_values_in_order(self) -> list[float]:
        m_to_v = {p.metric: p.value for p in self.points}
        return [float(m_to_v[m]) for m in METRIC_ORDER]


def _parse_latex_array_rows(array_block: str) -> list[dict[str, Any]]:
    """
    Parse rows like:
      \\text{Logistic regression} & \\text{Test} & 0.695 & 0.597 & 0.402 & 0.480 & 0.678 \\\\
    """
    row_re = re.compile(
        r"\\text\{(?P<model>[^}]*)\}\s*&\s*\\text\{(?P<split>[^}]*)\}\s*&\s*"
        r"(?P<accuracy>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<precision>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<recall>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<f1>-?\d+(?:\.\d+)?)\s*&\s*"
        r"(?P<roc_auc>-?\d+(?:\.\d+)?)",
        flags=re.MULTILINE,
    )

    out: list[dict[str, Any]] = []
    for m in row_re.finditer(array_block):
        d = m.groupdict()
        out.append(
            {
                "model": d["model"].strip(),
                "split": d["split"].strip(),
                "accuracy": float(d["accuracy"]),
                "precision": float(d["precision"]),
                "recall": float(d["recall"]),
                "f1": float(d["f1"]),
                "roc_auc": float(d["roc_auc"]),
            }
        )
    return out


def _extract_two_arrays_from_results_md(md_text: str) -> list[str]:
    # Capture blocks between \begin{array}{...} and \end{array}
    array_re = re.compile(r"\\begin\{array\}.*?\\end\{array\}", flags=re.DOTALL)
    blocks = array_re.findall(md_text)
    if len(blocks) < 2:
        raise ValueError(f"Expected at least 2 LaTeX array blocks, found {len(blocks)}")
    return blocks[:2]


def _model_class_from_model_name(model_name: str) -> str:
    if model_name.lower().startswith("baseline"):
        return "Baseline"
    if "logistic regression" in model_name.lower():
        return "Logistic regression"
    if "xgboost" in model_name.lower():
        return "XGBoost"
    # Fallback: use raw model name
    return model_name


def _plot_style(training_type: str) -> tuple[str, str]:
    # dashed = feature engineering; solid = embeddings
    if training_type == "feature_engineering":
        return "dashed", "#333333"
    if training_type == "text_embeddings":
        return "solid", "#333333"
    raise ValueError(f"Unknown training_type: {training_type}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-md",
        type=str,
        default=str(
            Path(__file__).resolve().parent
            / "results.md"
        ),
        help="Path to results.md containing the two LaTeX tables.",
    )
    parser.add_argument(
        "--outputs-name",
        type=str,
        default="test_metrics_linegraph",
        help="Subfolder under outputs/ to write results.json and results.png.",
    )
    args = parser.parse_args()

    results_md_path = Path(args.results_md)
    md_text = results_md_path.read_text(encoding="utf-8")
    array_blocks = _extract_two_arrays_from_results_md(md_text)

    # Table 0: feature engineered explainable text features
    # Table 1: text embeddings
    training_types = ["feature_engineering", "text_embeddings"]

    # Color depends on model class
    color_map = {
        "Baseline": "#1f77b4",  # matplotlib tab:blue
        "Logistic regression": "#ff7f0e",  # tab:orange
        "XGBoost": "#2ca02c",  # tab:green
    }
    default_color = "#7f7f7f"

    series_list: list[PlotSeries] = []
    for block, training_type in zip(array_blocks, training_types, strict=True):
        rows = _parse_latex_array_rows(block)
        for r in rows:
            if r["split"] != "Test":
                continue

            model_name = r["model"]
            model_class = _model_class_from_model_name(model_name)
            color = color_map.get(model_class, default_color)

            linestyle, _ = _plot_style(training_type)
            pretty_training = (
                "feature engineering" if training_type == "feature_engineering" else "text embeddings"
            )
            label = f"{model_class} ({pretty_training})"

            points = (
                SeriesPoint("Accuracy", r["accuracy"]),
                SeriesPoint("Precision", r["precision"]),
                SeriesPoint("Recall", r["recall"]),
                SeriesPoint("F1", r["f1"]),
            )
            series_list.append(
                PlotSeries(
                    label=label,
                    model_class=model_class,
                    training_type=training_type,
                    linestyle=linestyle,
                    color=color,
                    points=points,
                )
            )

    if not series_list:
        raise RuntimeError("No Test rows found in parsed tables.")

    # Create output dir
    ts = get_current_timestamp()
    out_dir = results_md_path.parent / "outputs" / args.outputs_name / ts
    out_dir.mkdir(parents=True, exist_ok=False)

    # Plot
    fig, ax = plt.subplots(figsize=(10, 6))
    x = list(range(len(METRIC_ORDER)))
    ax.set_xticks(x)
    ax.set_xticklabels(METRIC_ORDER)
    ax.set_ylabel("Test-set metric value (remove is positive)")
    ax.set_ylim(0.0, 1.02)
    ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
    ax.grid(True, axis="y", alpha=0.25)

    for s in series_list:
        ys = s.y_values_in_order()
        ls = "--" if s.linestyle == "dashed" else "-"
        ax.plot(x, ys, linestyle=ls, color=s.color, marker="o", linewidth=2, label=s.label)

    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    results_png_path = out_dir / "results.png"
    fig.savefig(results_png_path, dpi=200)

    # Save plot data
    results_json = {
        "source_results_md": str(results_md_path),
        "metric_order": METRIC_ORDER,
        "series": [
            {
                "label": s.label,
                "model_class": s.model_class,
                "training_type": s.training_type,
                "linestyle": s.linestyle,
                "color": s.color,
                "points": [{"metric": p.metric, "value": p.value} for p in s.points],
            }
            for s in series_list
        ],
        "output": {
            "results_png_path": str(results_png_path),
        },
    }
    results_json_path = out_dir / "results.json"
    results_json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")

    print("Wrote:", results_json_path)
    print("Wrote:", results_png_path)


if __name__ == "__main__":
    main()

