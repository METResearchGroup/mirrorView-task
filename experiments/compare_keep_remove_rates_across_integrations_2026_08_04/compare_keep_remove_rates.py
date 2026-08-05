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


def format_markdown_table(table: pd.DataFrame) -> str:
    """Format the crosstab as a markdown table with a decision column."""
    lines = [
        "| decision | Bluesky | Reddit | Twitter |",
        "|---|---:|---:|---:|",
    ]
    for decision in DECISION_ROWS:
        row = table.loc[decision]
        lines.append(
            f"| {decision} | {int(row['Bluesky'])} | {int(row['Reddit'])} | {int(row['Twitter'])} |"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    labels = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS)
    table = build_crosstab(labels)
    markdown = format_markdown_table(table)
    RESULTS_PATH.write_text(markdown, encoding="utf-8")
    print(markdown, end="")


if __name__ == "__main__":
    main()
