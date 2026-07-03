from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

# Ensure repo root is importable (so `lib/` works when running this script directly).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.timestamp_utils import get_current_timestamp  # noqa: E402

METRIC_ORDER = ["Accuracy", "Precision", "Recall", "F1"]


@dataclass(frozen=True)
class SeriesPoint:
    metric: str
    value: float


@dataclass(frozen=True)
class PlotSeries:
    label: str
    model_class: str
    ablation_variant: str
    linestyle: str
    color: str
    points: tuple[SeriesPoint, ...]

    def y_values_in_order(self) -> list[float]:
        m_to_v = {p.metric: p.value for p in self.points}
        return [float(m_to_v[m]) for m in METRIC_ORDER]


def _parse_latex_array_rows(array_block: str) -> list[dict[str, object]]:
    """
    Parse rows like:
      \\text{Logistic regression (baseline)} & \\text{Test} & 0.671 & 0.490 & 0.623 & 0.548 & 0.716 \\\\
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

    out: list[dict[str, object]] = []
    for m in row_re.finditer(array_block):
        d = m.groupdict()
        out.append(
            {
                "model": str(d["model"]).strip(),
                "split": str(d["split"]).strip(),
                "accuracy": float(d["accuracy"]),
                "precision": float(d["precision"]),
                "recall": float(d["recall"]),
                "f1": float(d["f1"]),
                "roc_auc": float(d["roc_auc"]),
            }
        )
    return out


def _extract_ablation_array_block(md_text: str) -> str:
    parts = md_text.split("### Ablation results", 1)
    if len(parts) != 2:
        raise ValueError("Could not find '### Ablation results' heading.")

    after_heading = parts[1]
    m = re.search(r"\\begin\{array\}.*?\\end\{array\}", after_heading, flags=re.DOTALL)
    if not m:
        raise ValueError("Could not find LaTeX array block under '### Ablation results'.")
    return m.group(0)


def _model_class_from_model_name(model_name: str) -> str:
    n = model_name.lower()
    if "logistic regression" in n:
        return "Logistic regression"
    if "xgboost" in n:
        return "XGBoost"
    return model_name


def _ablation_variant_from_model_name(model_name: str) -> str:
    n = model_name.lower()
    if "difference embedding" in n:
        return "difference embedding"
    if "only original" in n:
        return "only original post embedding"
    if "baseline" in n:
        return "baseline"
    return "variant"


def _linestyle_from_variant(variant: str) -> str:
    # Solid baseline, dashed ablations.
    return "-" if variant == "baseline" else "--"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-md",
        type=str,
        default=str(Path(__file__).resolve().parent / "results.md"),
        help="Path to results.md containing the Ablation results LaTeX table.",
    )
    parser.add_argument(
        "--outputs-name",
        type=str,
        default="study_2_ablations_test_metrics_linegraph",
        help="Subfolder under outputs/ to write results.json and results.png.",
    )
    args = parser.parse_args()

    results_md_path = Path(args.results_md)
    md_text = results_md_path.read_text(encoding="utf-8")
    ablation_array_block = _extract_ablation_array_block(md_text)

    rows = _parse_latex_array_rows(ablation_array_block)

    color_map = {
        "Logistic regression": "#ff7f0e",  # tab:orange
        "XGBoost": "#2ca02c",  # tab:green
    }
    default_color = "#7f7f7f"

    series_list: list[PlotSeries] = []
    for r in rows:
        if str(r["split"]) != "Test":
            continue

        model_name = str(r["model"])
        model_class = _model_class_from_model_name(model_name)
        variant = _ablation_variant_from_model_name(model_name)
        color = color_map.get(model_class, default_color)
        linestyle = _linestyle_from_variant(variant)

        label = f"{model_class} ({variant})"
        points = (
            SeriesPoint("Accuracy", float(r["accuracy"])),
            SeriesPoint("Precision", float(r["precision"])),
            SeriesPoint("Recall", float(r["recall"])),
            SeriesPoint("F1", float(r["f1"])),
        )

        series_list.append(
            PlotSeries(
                label=label,
                model_class=model_class,
                ablation_variant=variant,
                linestyle=linestyle,
                color=color,
                points=points,
            )
        )

    if not series_list:
        raise RuntimeError("No Test rows found in Ablation results table.")

    # Create output dir
    ts = get_current_timestamp()
    out_dir = results_md_path.parent / "outputs" / args.outputs_name / ts
    out_dir.mkdir(parents=True, exist_ok=False)

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
        ax.plot(x, ys, linestyle=s.linestyle, color=s.color, marker="o", linewidth=2, label=s.label)

    ax.legend(loc="best", fontsize=9)
    fig.tight_layout()

    results_png_path = out_dir / "results.png"
    fig.savefig(results_png_path, dpi=200)

    results_json = {
        "source_results_md": str(results_md_path),
        "metric_order": METRIC_ORDER,
        "series": [
            {
                "label": s.label,
                "model_class": s.model_class,
                "ablation_variant": s.ablation_variant,
                "linestyle": s.linestyle,
                "color": s.color,
                "points": [{"metric": p.metric, "value": p.value} for p in s.points],
            }
            for s in series_list
        ],
        "output": {"results_png_path": str(results_png_path)},
    }
    results_json_path = out_dir / "results.json"
    results_json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")

    print("Wrote:", results_json_path)
    print("Wrote:", results_png_path)


if __name__ == "__main__":
    main()

