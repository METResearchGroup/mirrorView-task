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
    min_y: float,
    max_y: float,
) -> list[tuple[float, float, str, str]]:
    """Return label positions that stay on the plot and do not overlap.

    The first number is the line's ending proportion. The second is the
    text position. A name never sits low enough for its letters to cross
    the x-axis.
    """
    ordered = sorted(points, key=lambda item: item[0])
    if not ordered:
        return []
    span = max(max_y - min_y, 0.01)
    gap = min(0.055, span / max(len(ordered) - 1, 1))
    placed: list[tuple[float, float, str, str]] = []
    for y_value, name, color in ordered:
        y_pos = min(max(y_value, min_y), max_y)
        if placed and y_pos < placed[-1][1] + gap:
            y_pos = placed[-1][1] + gap
        placed.append((y_value, y_pos, name, color))
    if placed[-1][1] > max_y:
        overflow = placed[-1][1] - max_y
        placed = [
            (y_value, y_pos - overflow, name, color) for y_value, y_pos, name, color in placed
        ]
    if placed[0][1] < min_y:
        step = span / max(len(placed) - 1, 1)
        placed = [
            (y_value, min_y + index * step, name, color)
            for index, (y_value, _y_pos, name, color) in enumerate(placed)
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
    label_size = evident.size("annotation", fig) * 0.75
    probe = ax.text(0, 0, "Mg", fontsize=label_size, alpha=0)
    fig.canvas.draw()
    text_height = probe.get_window_extent(fig.canvas.get_renderer()).height
    probe.remove()
    origin, raised = ax.transData.inverted().transform([(0, 0), (0, text_height)])
    half_height = (raised[1] - origin[1]) / 2
    min_y = half_height + 0.03
    max_y = 1 - half_height - 0.02
    label_x = len(xs) - 1 + 0.18
    for y_value, y_pos, name, color in _spread_labels(endpoints, min_y, max_y):
        if abs(y_pos - y_value) > 0.02:
            ax.plot([xs[-1], label_x - 0.04], [y_value, y_pos], color=color, linewidth=0.6, zorder=2)
        ax.text(
            label_x,
            y_pos,
            name,
            color=color,
            va="center",
            ha="left",
            fontsize=label_size,
            clip_on=False,
        )
    evident.titles(fig, title, subtitle=subtitle or None, source=CHART_SOURCE)
    figure_path.parent.mkdir(parents=True, exist_ok=True)
    evident.save(fig, figure_path)
    return figure_path
