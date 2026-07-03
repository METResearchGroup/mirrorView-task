from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator
from matplotlib.patches import Patch

# Ensure repo root is importable (so `lib/` works when running this script directly).
REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from lib.timestamp_utils import get_current_timestamp  # noqa: E402

METRIC_ORDER = ["Accuracy", "Precision", "Recall", "F1"]


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

def _bar_color_for_variant(variant: str) -> str:
    # Chosen to match the user's requested "baseline grey, only original green, difference embedding orange".
    if variant == "baseline":
        return "#9e9e9e"
    if variant == "only original post embedding":
        return "#2ca02c"
    if variant == "difference embedding":
        return "#ff7f0e"
    return "#7f7f7f"


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
        default="study_2_ablations_test_metrics_bargraph",
        help="Subfolder under outputs/ to write results.json and results.png.",
    )
    args = parser.parse_args()

    results_md_path = Path(args.results_md)
    md_text = results_md_path.read_text(encoding="utf-8")
    ablation_array_block = _extract_ablation_array_block(md_text)

    rows = _parse_latex_array_rows(ablation_array_block)

    # values[model_class][variant][metric] = value
    values: dict[str, dict[str, dict[str, float]]] = {}
    for r in rows:
        if str(r["split"]) != "Test":
            continue

        model_name = str(r["model"])
        model_class = _model_class_from_model_name(model_name)
        variant = _ablation_variant_from_model_name(model_name)

        values.setdefault(model_class, {}).setdefault(variant, {}).update(
            {
                "Accuracy": float(r["accuracy"]),
                "Precision": float(r["precision"]),
                "Recall": float(r["recall"]),
                "F1": float(r["f1"]),
            }
        )

    if not values:
        raise RuntimeError("No Test rows found in Ablation results table.")

    # Create output dir
    ts = get_current_timestamp()
    out_dir = results_md_path.parent / "outputs" / args.outputs_name / ts
    out_dir.mkdir(parents=True, exist_ok=False)

    # Two panels (matching "two sets of bar graphs": logistic regression vs XGBoost).
    model_panels = ["Logistic regression", "XGBoost"]
    n_panels = len(model_panels)

    fig, axes = plt.subplots(1, n_panels, figsize=(14, 5), sharey=True)
    if n_panels == 1:
        axes = [axes]

    metric_x = list(range(len(METRIC_ORDER)))
    group_width = 0.22
    offsets = [-group_width, 0.0, group_width]  # baseline, only-original, difference

    variants = ["baseline", "only original post embedding", "difference embedding"]

    for ax, model_class in zip(axes, model_panels, strict=False):
        for v_i, variant in enumerate(variants):
            ys = [values.get(model_class, {}).get(variant, {}).get(m, 0.0) for m in METRIC_ORDER]
            xs = [x + offsets[v_i] for x in metric_x]
            ax.bar(xs, ys, width=group_width, color=_bar_color_for_variant(variant), edgecolor="black", linewidth=0.3)

        ax.set_xticks(metric_x)
        ax.set_xticklabels(METRIC_ORDER)
        ax.set_title(model_class)
        ax.set_ylim(0.0, 1.02)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.grid(True, axis="y", alpha=0.25)

    axes[0].set_ylabel("Test-set metric value (remove is positive)")

    legend_handles = [Patch(facecolor=_bar_color_for_variant(v), edgecolor="black", label=v) for v in variants]
    fig.legend(handles=legend_handles, loc="upper center", ncol=3, frameon=False)

    fig.tight_layout(rect=[0, 0, 1, 0.93])

    results_png_path = out_dir / "results.png"
    fig.savefig(results_png_path, dpi=200)

    results_json = {
        "source_results_md": str(results_md_path),
        "metric_order": METRIC_ORDER,
        "values": {
            model_class: {
                ablation_variant: {
                    metric: float(values[model_class][ablation_variant][metric])
                    for metric in METRIC_ORDER
                }
                for ablation_variant in values[model_class].keys()
            }
            for model_class in values.keys()
        },
        "output": {"results_png_path": str(results_png_path)},
    }
    results_json_path = out_dir / "results.json"
    results_json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")

    print("Wrote:", results_json_path)
    print("Wrote:", results_png_path)


if __name__ == "__main__":
    main()

