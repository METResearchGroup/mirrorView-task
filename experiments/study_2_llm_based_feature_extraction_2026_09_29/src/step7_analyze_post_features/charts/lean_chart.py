"""Horizontal bars of the top features for left-leaning and right-leaning pairs."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CHART_PRESET,
    CHART_SOURCE,
    LOCAL_OUTPUT_DIR,
    TOP_BY_LEAN_KEY,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.common import (
    load_evident,
    short_label,
)

FIGURE_PATH = LOCAL_OUTPUT_DIR / "step7_analyze_post_features" / "figures" / "lean.svg"


def _panel(ax, frame: pd.DataFrame, evident, color: str) -> None:
    ordered = frame.sort_values("rank", ascending=False)
    labels = [short_label(name, 22) for name in ordered["name"]]
    bars = ax.barh(labels, ordered["n_pairs"], color=color)
    evident.value_labels(ax, bars)
    n_pairs = int(frame["n_group_pairs"].iloc[0])
    ax.set_title(f"{frame['group'].iloc[0].title()} ({n_pairs:,} pairs)")


def main() -> Path:
    """Draw the lean chart and write its SVG."""
    evident = load_evident()
    table = pd.read_csv(LOCAL_OUTPUT_DIR / TOP_BY_LEAN_KEY)
    fig, axes = evident.figure(CHART_PRESET, ncols=2, rows=10)
    colors = {"left": "#0072B2", "right": "#D55E00"}
    for ax, group in zip(axes, ("left", "right"), strict=True):
        _panel(ax, table.loc[table["group"] == group], evident, colors[group])
    left_n = int(table.loc[table["group"] == "left", "n_group_pairs"].iloc[0])
    right_n = int(table.loc[table["group"] == "right", "n_group_pairs"].iloc[0])
    evident.titles(
        fig,
        "Most common features by the original post's lean",
        subtitle=(
            "Each bar counts pairs where the feature is present. "
            f"Left: {left_n:,} pairs. Right: {right_n:,} pairs."
        ),
        source=CHART_SOURCE,
    )
    fig.subplots_adjust(left=0.28, right=0.98, wspace=0.45, bottom=0.08, top=0.78)
    FIGURE_PATH.parent.mkdir(parents=True, exist_ok=True)
    evident.save(fig, FIGURE_PATH)
    return FIGURE_PATH


if __name__ == "__main__":
    main()
