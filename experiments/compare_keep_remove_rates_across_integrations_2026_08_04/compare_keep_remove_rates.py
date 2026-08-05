"""Crosstab keep/remove labels vs platform for Study Phase 2 Part 2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import (
    STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS,
    STUDY_PHASE_2_PART_2_STIMULI,
)

EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EXPERIMENT_DIR / "RESULTS.md"

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


def format_results_markdown(
    platform_counts: pd.DataFrame,
    platform_proportions: pd.DataFrame,
    platform_toxicity_proportions: pd.DataFrame,
) -> str:
    """Render counts, platform proportions, then platform×toxicity proportions."""
    return (
        f"{format_counts_table(platform_counts)}\n\n"
        f"{format_proportions_table(platform_proportions)}\n\n"
        f"{format_proportions_table(platform_toxicity_proportions)}\n"
    )


def main() -> None:
    labeled_posts = load_labeled_posts()
    platform_counts = build_platform_crosstab(labeled_posts)
    platform_proportions = column_proportions(platform_counts)
    platform_toxicity_counts = build_platform_toxicity_crosstab(labeled_posts)
    platform_toxicity_proportions = column_proportions(platform_toxicity_counts)
    markdown = format_results_markdown(
        platform_counts,
        platform_proportions,
        platform_toxicity_proportions,
    )
    RESULTS_PATH.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
