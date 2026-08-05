"""Crosstab keep/remove labels vs platform for Study Phase 2 Part 2."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.colors import to_rgb
from matplotlib.patches import Patch

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_2_STIMULI,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EXPERIMENT_DIR / "RESULTS.md"
FIGURE_PATH = EXPERIMENT_DIR / "platform_toxicity_proportions.png"

PLATFORM_BY_PREFIX: dict[str, str] = {
    "bluesky": "Bluesky",
    "reddit": "Reddit",
    "twitter": "Twitter",
}
PLATFORM_COLUMNS: tuple[str, ...] = ("Bluesky", "Reddit", "Twitter")
DECISION_ROWS: tuple[str, ...] = ("keep", "remove")

TOXICITY_BY_SAMPLE_TYPE: dict[str, str] = {
    "sample_low_toxicity": "low toxicity",
    "sample_middle_toxicity": "medium toxicity",
    "sample_high_toxicity": "high toxicity",
}
TOXICITY_ORDER: tuple[str, ...] = (
    "low toxicity",
    "medium toxicity",
    "high toxicity",
)
PLATFORM_TOXICITY_COLUMNS: tuple[str, ...] = tuple(
    f"{platform} {toxicity}"
    for platform in PLATFORM_COLUMNS
    for toxicity in TOXICITY_ORDER
)

PLATFORM_COLORS: dict[str, str] = {
    "Bluesky": "#2F6FED",
    "Reddit": "#E36A2E",
    "Twitter": "#2A9D8F",
}
TOXICITY_OPACITY: dict[str, float] = {
    "low toxicity": 0.35,
    "medium toxicity": 0.65,
    "high toxicity": 1.0,
}
KEEP_OPACITY_SCALE = 0.45
PLATFORM_GROUP_GAP = 0.8
FIGURE_DPI = 200

PROPORTION_DECIMALS = 4


def derive_platform(message_id: str) -> str:
    """Map ``message_id`` prefix (before first ``_``) to a display platform name."""
    prefix = str(message_id).split("_", 1)[0]
    try:
        return PLATFORM_BY_PREFIX[prefix]
    except KeyError as exc:
        raise ValueError(
            f"Unknown platform prefix {prefix!r} in message_id={message_id!r}"
        ) from exc


def derive_toxicity_label(sample_toxicity_type: str) -> str:
    """Map stimuli ``sample_toxicity_type`` to a short display label."""
    key = str(sample_toxicity_type).strip()
    try:
        return TOXICITY_BY_SAMPLE_TYPE[key]
    except KeyError as exc:
        raise ValueError(
            f"Unknown sample_toxicity_type {sample_toxicity_type!r}"
        ) from exc


def load_labeled_posts() -> pd.DataFrame:
    """Load keep/remove labels joined to stimuli toxicity."""
    labels = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS)
    stimuli = load_dataset(STUDY_PHASE_2_PART_2_STIMULI)[
        ["post_primary_key", "sample_toxicity_type"]
    ]
    merged = labels.merge(
        stimuli,
        left_on="message_id",
        right_on="post_primary_key",
        how="left",
        validate="one_to_one",
    )
    missing = int(merged["sample_toxicity_type"].isna().sum())
    if missing:
        raise ValueError(
            f"{missing} labeled posts missing stimuli toxicity after merge"
        )
    frame = merged.copy()
    frame["decision"] = frame["decision"].astype(str).str.lower().str.strip()
    frame["platform"] = frame["message_id"].map(derive_platform)
    frame["toxicity"] = frame["sample_toxicity_type"].map(derive_toxicity_label)
    frame["platform_toxicity"] = frame["platform"] + " " + frame["toxicity"]
    return frame


def build_platform_crosstab(labeled_posts: pd.DataFrame) -> pd.DataFrame:
    """Return a 2×3 keep/remove × platform count matrix."""
    table = pd.crosstab(labeled_posts["decision"], labeled_posts["platform"])
    return (
        table.reindex(index=list(DECISION_ROWS), columns=list(PLATFORM_COLUMNS))
        .fillna(0)
        .astype(int)
    )


def build_platform_toxicity_crosstab(labeled_posts: pd.DataFrame) -> pd.DataFrame:
    """Return keep/remove × (platform + toxicity) count matrix."""
    table = pd.crosstab(
        labeled_posts["decision"], labeled_posts["platform_toxicity"]
    )
    return (
        table.reindex(
            index=list(DECISION_ROWS), columns=list(PLATFORM_TOXICITY_COLUMNS)
        )
        .fillna(0)
        .astype(int)
    )


def column_proportions(counts: pd.DataFrame) -> pd.DataFrame:
    """Keep/remove share within each column (columns sum to 1)."""
    totals = counts.sum(axis=0).replace(0, pd.NA)
    return (counts / totals).astype(float)


def format_counts_table(table: pd.DataFrame) -> str:
    """Format an integer crosstab as a markdown table."""
    columns = list(table.columns)
    header = "| decision | " + " | ".join(columns) + " |"
    separator = "|---|" + "|".join(["---:"] * len(columns)) + "|"
    lines = [header, separator]
    for decision in DECISION_ROWS:
        cells = " | ".join(str(int(table.loc[decision, col])) for col in columns)
        lines.append(f"| {decision} | {cells} |")
    return "\n".join(lines)


def format_proportions_table(table: pd.DataFrame) -> str:
    """Format a proportion crosstab as a markdown table."""
    columns = list(table.columns)
    header = "| decision | " + " | ".join(columns) + " |"
    separator = "|---|" + "|".join(["---:"] * len(columns)) + "|"
    lines = [header, separator]
    for decision in DECISION_ROWS:
        cells = " | ".join(
            f"{float(table.loc[decision, col]):.{PROPORTION_DECIMALS}f}"
            for col in columns
        )
        lines.append(f"| {decision} | {cells} |")
    return "\n".join(lines)


def parse_platform_toxicity_column(column: str) -> tuple[str, str]:
    """Split a crosstab column label into platform and toxicity."""
    for platform in PLATFORM_COLUMNS:
        prefix = f"{platform} "
        if column.startswith(prefix):
            return platform, column.removeprefix(prefix)
    raise ValueError(f"Unrecognized platform×toxicity column: {column!r}")


def bar_x_positions(n_columns: int, group_size: int) -> list[float]:
    """X positions with a gap after each platform group."""
    positions: list[float] = []
    offset = 0.0
    for index in range(n_columns):
        if index > 0 and index % group_size == 0:
            offset += PLATFORM_GROUP_GAP
        positions.append(float(index) + offset)
    return positions


def plot_platform_toxicity_proportions(
    proportions: pd.DataFrame, output_path: Path
) -> None:
    """Stacked keep/remove bars; platform hue, toxicity opacity; crosstab order."""
    columns = list(proportions.columns)
    if columns != list(PLATFORM_TOXICITY_COLUMNS):
        raise ValueError("Proportion columns must match PLATFORM_TOXICITY_COLUMNS order")

    x_positions = bar_x_positions(len(columns), group_size=len(TOXICITY_ORDER))
    keep_values = [float(proportions.loc["keep", col]) for col in columns]
    remove_values = [float(proportions.loc["remove", col]) for col in columns]

    keep_colors: list[tuple[float, float, float, float]] = []
    remove_colors: list[tuple[float, float, float, float]] = []
    for column in columns:
        platform, toxicity = parse_platform_toxicity_column(column)
        rgb = to_rgb(PLATFORM_COLORS[platform])
        opacity = TOXICITY_OPACITY[toxicity]
        keep_colors.append((*rgb, opacity * KEEP_OPACITY_SCALE))
        remove_colors.append((*rgb, opacity))

    fig, ax = plt.subplots(figsize=(12, 5.5))
    ax.bar(
        x_positions,
        keep_values,
        width=0.8,
        color=keep_colors,
        edgecolor="#333333",
        linewidth=0.6,
        label="keep",
    )
    ax.bar(
        x_positions,
        remove_values,
        width=0.8,
        bottom=keep_values,
        color=remove_colors,
        edgecolor="#333333",
        linewidth=0.6,
        label="remove",
    )

    toxicity_tick_labels = [
        parse_platform_toxicity_column(column)[1].removesuffix(" toxicity")
        for column in columns
    ]
    ax.set_xticks(x_positions)
    ax.set_xticklabels(toxicity_tick_labels)
    ax.set_ylim(0.0, 1.0)
    ax.set_ylabel("Proportion")
    ax.set_xlabel("Toxicity within platform")
    ax.set_title("Keep/remove proportions by platform × toxicity")
    ax.axhline(0.5, color="#888888", linestyle="--", linewidth=0.8, alpha=0.7)
    ax.grid(True, axis="y", alpha=0.25)

    group_size = len(TOXICITY_ORDER)
    for platform_index, platform in enumerate(PLATFORM_COLUMNS):
        group = x_positions[
            platform_index * group_size : (platform_index + 1) * group_size
        ]
        ax.text(
            (group[0] + group[-1]) / 2.0,
            -0.12,
            platform,
            transform=ax.get_xaxis_transform(),
            ha="center",
            va="top",
            fontsize=11,
            fontweight="bold",
            color=PLATFORM_COLORS[platform],
        )

    platform_handles = [
        Patch(facecolor=PLATFORM_COLORS[platform], edgecolor="#333333", label=platform)
        for platform in PLATFORM_COLUMNS
    ]
    toxicity_handles = [
        Patch(
            facecolor=(0.2, 0.2, 0.2, TOXICITY_OPACITY[toxicity]),
            edgecolor="#333333",
            label=toxicity.removesuffix(" toxicity"),
        )
        for toxicity in TOXICITY_ORDER
    ]
    decision_handles = [
        Patch(
            facecolor=(0.4, 0.4, 0.4, KEEP_OPACITY_SCALE),
            edgecolor="#333333",
            label="keep",
        ),
        Patch(facecolor=(0.4, 0.4, 0.4, 1.0), edgecolor="#333333", label="remove"),
    ]
    legend_platforms = ax.legend(
        handles=platform_handles, title="Platform", loc="upper left"
    )
    ax.add_artist(legend_platforms)
    legend_toxicity = ax.legend(
        handles=toxicity_handles, title="Toxicity", loc="upper center"
    )
    ax.add_artist(legend_toxicity)
    ax.legend(handles=decision_handles, title="Decision", loc="upper right")

    fig.tight_layout()
    fig.subplots_adjust(bottom=0.18)
    fig.savefig(output_path, dpi=FIGURE_DPI)
    plt.close(fig)


def format_results_markdown(
    platform_counts: pd.DataFrame,
    platform_proportions: pd.DataFrame,
    platform_toxicity_proportions: pd.DataFrame,
) -> str:
    """Render counts, platform proportions, platform×toxicity proportions, and figure."""
    return (
        f"{format_counts_table(platform_counts)}\n\n"
        f"{format_proportions_table(platform_proportions)}\n\n"
        f"{format_proportions_table(platform_toxicity_proportions)}\n\n"
        f"![Keep/remove proportions by platform × toxicity]"
        f"(platform_toxicity_proportions.png)\n"
    )


def main() -> None:
    labeled_posts = load_labeled_posts()
    platform_counts = build_platform_crosstab(labeled_posts)
    platform_proportions = column_proportions(platform_counts)
    platform_toxicity_counts = build_platform_toxicity_crosstab(labeled_posts)
    platform_toxicity_proportions = column_proportions(platform_toxicity_counts)
    plot_platform_toxicity_proportions(
        platform_toxicity_proportions, FIGURE_PATH
    )
    markdown = format_results_markdown(
        platform_counts,
        platform_proportions,
        platform_toxicity_proportions,
    )
    RESULTS_PATH.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
