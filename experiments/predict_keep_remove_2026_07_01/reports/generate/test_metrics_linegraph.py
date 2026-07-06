"""Line graph comparing hand-crafted features vs embedding models (Study 1) from results.md."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from experiments.predict_keep_remove_2026_07_01.reports.parse_results_md import (
    extract_first_n_array_blocks,
    parse_latex_array_rows,
)
from experiments.predict_keep_remove_2026_07_01.reports.paths import DEFAULT_RESULTS_MD, make_output_dir
from experiments.predict_keep_remove_2026_07_01.reports.plot_style import (
    DEFAULT_MODEL_COLOR,
    METRIC_ORDER,
    MODEL_CLASS_COLORS,
    PlotSeries,
    SeriesPoint,
    model_class_from_model_name,
    training_type_linestyle,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--results-md",
        type=str,
        default=str(DEFAULT_RESULTS_MD),
        help="Path to results.md containing the two LaTeX tables.",
    )
    parser.add_argument(
        "--outputs-name",
        type=str,
        default="test_metrics_linegraph",
        help="Subfolder under reports/outputs/ to write results.json and results.png.",
    )
    args = parser.parse_args()

    results_md_path = Path(args.results_md)
    md_text = results_md_path.read_text(encoding="utf-8")
    array_blocks = extract_first_n_array_blocks(md_text, n=2)

    training_types = ["feature_engineering", "text_embeddings"]
    series_list: list[PlotSeries] = []

    for block, training_type in zip(array_blocks, training_types, strict=True):
        rows = parse_latex_array_rows(block)
        for r in rows:
            if r["split"] != "Test":
                continue

            model_name = str(r["model"])
            model_class = model_class_from_model_name(model_name)
            color = MODEL_CLASS_COLORS.get(model_class, DEFAULT_MODEL_COLOR)
            linestyle = training_type_linestyle(training_type)
            pretty_training = (
                "feature engineering" if training_type == "feature_engineering" else "text embeddings"
            )
            label = f"{model_class} ({pretty_training})"

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
                    training_type=training_type,
                    linestyle=linestyle,
                    color=color,
                    points=points,
                )
            )

    if not series_list:
        raise RuntimeError("No Test rows found in parsed tables.")

    out_dir = make_output_dir(args.outputs_name)

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
        "output": {"results_png_path": str(results_png_path)},
    }
    results_json_path = out_dir / "results.json"
    results_json_path.write_text(json.dumps(results_json, indent=2), encoding="utf-8")

    print("Wrote:", results_json_path)
    print("Wrote:", results_png_path)


if __name__ == "__main__":
    main()
