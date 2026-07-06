"""Bar chart of Study 2 embedding ablation test-set metrics from results.md."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from matplotlib.ticker import MaxNLocator

from experiments.predict_keep_remove_2026_07_01.reports.parse_results_md import (
    extract_ablation_array_block,
    parse_latex_array_rows,
)
from experiments.predict_keep_remove_2026_07_01.reports.paths import DEFAULT_RESULTS_MD, make_output_dir
from experiments.predict_keep_remove_2026_07_01.reports.plot_style import (
    METRIC_ORDER,
    ablation_bar_color,
    ablation_model_class_from_model_name,
    ablation_variant_from_model_name,
    ablation_variant_label,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-md",
        type=str,
        default=str(DEFAULT_RESULTS_MD),
        help="Path to results.md containing the Ablation results LaTeX table.",
    )
    parser.add_argument(
        "--outputs-name",
        type=str,
        default="study_2_ablations_test_metrics_bargraph",
        help="Subfolder under reports/outputs/ to write results.json and results.png.",
    )
    args = parser.parse_args()

    results_md_path = Path(args.results_md)
    md_text = results_md_path.read_text(encoding="utf-8")
    ablation_array_block = extract_ablation_array_block(md_text)
    rows = parse_latex_array_rows(ablation_array_block)

    values: dict[str, dict[str, dict[str, float]]] = {}
    for r in rows:
        if str(r["split"]) != "Test":
            continue

        model_name = str(r["model"])
        model_class = ablation_model_class_from_model_name(model_name)
        variant = ablation_variant_from_model_name(model_name)

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

    out_dir = make_output_dir(args.outputs_name)

    model_panels = ["Logistic regression", "XGBoost"]
    fig, axes = plt.subplots(1, len(model_panels), figsize=(14, 5), sharey=True)
    if len(model_panels) == 1:
        axes = [axes]

    metric_x = list(range(len(METRIC_ORDER)))
    group_width = 0.22
    offsets = [-group_width, 0.0, group_width]
    variants = ["baseline", "only original post embedding", "difference embedding"]

    for ax, model_class in zip(axes, model_panels, strict=False):
        for v_i, variant in enumerate(variants):
            ys = [values.get(model_class, {}).get(variant, {}).get(m, 0.0) for m in METRIC_ORDER]
            xs = [x + offsets[v_i] for x in metric_x]
            ax.bar(
                xs,
                ys,
                width=group_width,
                color=ablation_bar_color(variant),
                edgecolor="black",
                linewidth=0.3,
            )

        ax.set_xticks(metric_x)
        ax.set_xticklabels(METRIC_ORDER)
        ax.set_title(model_class)
        ax.set_ylim(0.0, 1.02)
        ax.yaxis.set_major_locator(MaxNLocator(nbins=6))
        ax.grid(True, axis="y", alpha=0.25)

    axes[0].set_ylabel("Test-set metric value (remove is positive)")

    legend_handles = [
        Patch(facecolor=ablation_bar_color(v), edgecolor="black", label=ablation_variant_label(v))
        for v in variants
    ]
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
