"""Proportion of pairs with each feature across low, medium, and high toxicity."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    LOCAL_OUTPUT_DIR,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.proportion_lines import (
    draw_proportion_lines,
)

TABLE_PATH = LOCAL_OUTPUT_DIR / "analyses" / "feature_proportions_by_toxicity.csv"
FIGURE_PATH = LOCAL_OUTPUT_DIR / "step7_analyze_post_features" / "figures" / "toxicity_proportions.svg"


def main() -> Path:
    """Draw the toxicity proportion lines and write the SVG."""
    table = pd.read_csv(TABLE_PATH)
    return draw_proportion_lines(
        table,
        ["low", "medium", "high"],
        ["Low", "Medium", "High"],
        "Hostility rises with toxicity. Policy argument falls.",
        "Each line is one feature. Y is the fraction of pairs in that toxicity group where the feature is present.",
        FIGURE_PATH,
        x_axis_label="Toxicity of the original post",
    )


if __name__ == "__main__":
    main()
