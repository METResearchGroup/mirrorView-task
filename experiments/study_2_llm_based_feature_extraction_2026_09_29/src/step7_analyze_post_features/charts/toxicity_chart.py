"""Horizontal bars of the top features at low, medium, and high toxicity."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CHART_PRESET,
    CHART_SOURCE,
    LOCAL_OUTPUT_DIR,
    TOP_BY_TOXICITY_KEY,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.common import (
    load_evident,
    short_label,
)

FIGURE_PATH = LOCAL_OUTPUT_DIR / "step7_analyze_post_features" / "figures" / "toxicity.svg"


def main() -> Path:
    """Draw the toxicity chart and write its SVG."""
    evident = load_evident()
    table = pd.read_csv(LOCAL_OUTPUT_DIR / TOP_BY_TOXICITY_KEY)
    fig, axes = evident.figure(CHART_PRESET, nrows=3, ncols=1, rows=10)
    colors = {"low": "#009E73", "medium": "#E69F00", "high": "#D55E00"}
    for ax, group in zip(axes, ("low", "medium", "high"), strict=True):
        frame = table.loc[table["group"] == group]
        ordered = frame.sort_values("rank", ascending=False)
        labels = [short_label(name, 36) for name in ordered["name"]]
        bars = ax.barh(labels, ordered["n_pairs"], color=colors[group])
        evident.value_labels(ax, bars)
        n_pairs = int(frame["n_group_pairs"].iloc[0])
        ax.set_title(f"{group.title()} ({n_pairs:,} pairs)")
    counts = {
        group: int(table.loc[table["group"] == group, "n_group_pairs"].iloc[0])
        for group in ("low", "medium", "high")
    }
    evident.titles(
        fig,
        "Most common features by the original post's toxicity",
        subtitle=(
            "Each bar counts pairs where the feature is present. "
            f"Low: {counts['low']:,}. Medium: {counts['medium']:,}. High: {counts['high']:,}."
        ),
        source=CHART_SOURCE,
    )
    fig.subplots_adjust(left=0.42, right=0.98, hspace=0.35, bottom=0.06, top=0.9)
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    evident.save(fig, FIGURE_PATH)
    return FIGURE_PATH


if __name__ == "__main__":
    main()
