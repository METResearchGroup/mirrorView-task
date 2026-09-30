"""Line chart of feature proportions, with a few series labeled."""

from __future__ import annotations

from pathlib import Path

import matplotlib.ticker as mticker
import pandas as pd

from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    CHART_PRESET,
    CHART_SOURCE,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.src.step7_analyze_post_features.charts.common import (
    load_evident,
)

CHARCOAL = "#3D4A5C"
GREEN = "#3B8E3D"
RED = "#D62728"
GREY = "#767676"

CHARCOAL_NAMES = (
    "Political Actor and Institution Criticism",
    "Specific Political and Institutional References",
    "Political and Institutional Targets",
)
GREEN_NAMES = (
    "Substantive Policy and Institutional Claims",
    "Policy Advocacy and Tradeoff Arguments",
)
RED_NAMES = (
    "Escalatory Partisan Hostility",
    "Hostile Outrage Venting",
    "Sweeping Unsubstantiated Political Accusations",
    "Partisan Mockery and Taunting",
    "Derogatory Labels and Epithets",
)


def _series(table: pd.DataFrame, name: str, group_order: list[str]) -> list[float]:
    frame = table.loc[table["name"] == name]
    values: list[float] = []
    for group in group_order:
        match = frame.loc[frame["group"].astype(str) == str(group), "proportion"]
        if match.empty:
            raise ValueError(f"missing proportion for {name} in {group}")
        values.append(float(match.iloc[0]))
    return values


def _spread_labels(
    points: list[tuple[float, str, str]],
) -> list[tuple[float, float, str, str]]:
    """Return label positions that stay near each line and do not overlap.

    The first number is the line's ending proportion. The second is the
    text position, which moves only when two names would collide.
    """
    ordered = sorted(points, key=lambda item: item[0])
    gap = 0.07
    placed: list[tuple[float, float, str, str]] = []
    for y_value, name, color in ordered:
        y_pos = y_value
        if placed and y_pos < placed[-1][1] + gap:
            y_pos = placed[-1][1] + gap
        placed.append((y_value, y_pos, name, color))
    if placed and placed[-1][1] > 1.02:
        shift = placed[-1][1] - 1.02
        placed = [
            (y_value, y_pos - shift, name, color) for y_value, y_pos, name, color in placed
        ]
    return placed


def draw_proportion_lines(
    table: pd.DataFrame,
    group_order: list[str],
    x_labels: list[str],
    title: str,
    subtitle: str | None,
    figure_path: Path,
    x_axis_label: str | None = None,
) -> Path:
    """Draw one grey line per feature and label the highlighted series.

    Parameters
    ----------
    table
        Rows with ``name``, ``group``, and ``proportion``.
    group_order
        X-axis groups, left to right.
    x_labels
        Tick text for those groups.
    title
        Chart title.
    subtitle
        Optional second line under the title. These charts leave it empty.
    figure_path
        SVG destination.

    Returns
    -------
    pathlib.Path
        Written SVG path.
    """
    evident = load_evident()
    fig, ax = evident.figure(CHART_PRESET, rows=12)
    fig.set_size_inches(12.5, fig.get_figheight())
    xs = list(range(len(group_order)))
    highlighted = (
        {name: CHARCOAL for name in CHARCOAL_NAMES}
        | {name: GREEN for name in GREEN_NAMES}
        | {name: RED for name in RED_NAMES}
    )
    for name in sorted(table["name"].unique()):
        if name in highlighted:
            continue
        ax.plot(
            xs,
            _series(table, name, group_order),
            color=GREY,
            alpha=0.5,
            marker="o",
            linewidth=1.25,
            markersize=3.5,
            zorder=1,
        )
    endpoints: list[tuple[float, str, str]] = []
    for name, color in highlighted.items():
        ys = _series(table, name, group_order)
        ax.plot(
            xs,
            ys,
            color=color,
            marker="o",
            linewidth=2.25,
            markersize=5.5,
            zorder=3,
        )
        endpoints.append((ys[-1], name, color))
    ax.set_xticks(xs)
    ax.set_xticklabels(x_labels)
    ax.set_xlim(-0.15, len(xs) - 1 + 3.15)
    ax.set_ylim(0, 1)
    ax.set_ylabel("Proportion of pairs")
    if x_axis_label:
        ax.set_xlabel(x_axis_label)
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.3f"))
    label_x = len(xs) - 1 + 0.18
    for y_value, y_pos, name, color in _spread_labels(endpoints):
        if abs(y_pos - y_value) > 0.02:
            ax.plot([xs[-1], label_x - 0.04], [y_value, y_pos], color=color, linewidth=0.6, zorder=2)
        ax.text(
            label_x,
            y_pos,
            name,
            color=color,
            va="center",
            ha="left",
            fontsize=evident.size("annotation", fig),
            clip_on=False,
        )
    evident.titles(fig, title, subtitle=subtitle or None, source=CHART_SOURCE)
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    evident.save(fig, figure_path)
    return figure_path
