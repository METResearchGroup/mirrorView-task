"""Crosstab keep/remove labels vs platform for Study Phase 2 Part 2."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

EXPERIMENT_DIR = Path(__file__).resolve().parent
RESULTS_PATH = EXPERIMENT_DIR / "RESULTS.md"

PLATFORM_BY_PREFIX: dict[str, str] = {
    "bluesky": "Bluesky",
    "reddit": "Reddit",
    "twitter": "Twitter",
}
PLATFORM_COLUMNS: tuple[str, ...] = ("Bluesky", "Reddit", "Twitter")
DECISION_ROWS: tuple[str, ...] = ("keep", "remove")


def derive_platform(message_id: str) -> str:
    """Map ``message_id`` prefix (before first ``_``) to a display platform name."""
    prefix = str(message_id).split("_", 1)[0]
    try:
        return PLATFORM_BY_PREFIX[prefix]
    except KeyError as exc:
        raise ValueError(
            f"Unknown platform prefix {prefix!r} in message_id={message_id!r}"
        ) from exc


def build_crosstab(labels: pd.DataFrame) -> pd.DataFrame:
    """Return a 2×3 keep/remove × platform count matrix."""
    frame = labels.copy()
    frame["decision"] = frame["decision"].astype(str).str.lower().str.strip()
    frame["platform"] = frame["message_id"].map(derive_platform)
    table = pd.crosstab(frame["decision"], frame["platform"])
    return table.reindex(index=list(DECISION_ROWS), columns=list(PLATFORM_COLUMNS)).fillna(0).astype(int)


PROPORTION_DECIMALS = 4


def column_proportions(counts: pd.DataFrame) -> pd.DataFrame:
    """Keep/remove share within each platform (columns sum to 1)."""
    totals = counts.sum(axis=0).replace(0, pd.NA)
    return (counts / totals).astype(float)


def format_counts_table(table: pd.DataFrame) -> str:
    """Format count crosstab as a markdown table."""
    lines = [
        "| decision | Bluesky | Reddit | Twitter |",
        "|---|---:|---:|---:|",
    ]
    for decision in DECISION_ROWS:
        row = table.loc[decision]
        lines.append(
            f"| {decision} | {int(row['Bluesky'])} | {int(row['Reddit'])} | {int(row['Twitter'])} |"
        )
    return "\n".join(lines)


def format_proportions_table(table: pd.DataFrame) -> str:
    """Format per-platform keep/remove proportions as a markdown table."""
    lines = [
        "| decision | Bluesky | Reddit | Twitter |",
        "|---|---:|---:|---:|",
    ]
    for decision in DECISION_ROWS:
        row = table.loc[decision]
        lines.append(
            "| {decision} | {bluesky:.{n}f} | {reddit:.{n}f} | {twitter:.{n}f} |".format(
                decision=decision,
                bluesky=float(row["Bluesky"]),
                reddit=float(row["Reddit"]),
                twitter=float(row["Twitter"]),
                n=PROPORTION_DECIMALS,
            )
        )
    return "\n".join(lines)


def format_results_markdown(counts: pd.DataFrame, proportions: pd.DataFrame) -> str:
    """Render counts then per-platform proportions."""
    return (
        f"{format_counts_table(counts)}\n\n"
        f"{format_proportions_table(proportions)}\n"
    )


def main() -> None:
    labels = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS)
    counts = build_crosstab(labels)
    proportions = column_proportions(counts)
    markdown = format_results_markdown(counts, proportions)
    RESULTS_PATH.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
