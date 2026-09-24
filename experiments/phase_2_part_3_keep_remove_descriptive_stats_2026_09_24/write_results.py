"""Format and write RESULTS.md and output CSV mirrors.

Run from repo root::

    PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.phase_2_part_3_keep_remove_descriptive_stats_2026_09_24.platform_rates import (
    PROPORTION_DECIMALS,
)

OUTPUT_CSV_NAMES = (
    "platform_counts.csv",
    "platform_proportions.csv",
    "platform_toxicity_proportions.csv",
    "four_cell_counts.csv",
    "funnel.csv",
)

RESULTS_SECTIONS = (
    "Platform counts",
    "Platform proportions",
    "Platform by toxicity proportions",
    "Four-cell counts",
    "Vote funnel",
)


def format_counts_table(
    table: pd.DataFrame, decision_rows: tuple[str, ...]
) -> str:
    """Format an integer crosstab as a markdown pipe table.

    Parameters
    ----------
    table
        Integer crosstab indexed by decision rows and platform columns.
    decision_rows
        Row order for the markdown table.

    Returns
    -------
    str
        Markdown pipe table with header ``| decision | ... |``.
    """
    columns = list(table.columns)
    header = "| decision | " + " | ".join(columns) + " |"
    separator = "|---|" + "|".join(["---:"] * len(columns)) + "|"
    lines = [header, separator]
    for decision in decision_rows:
        cells = " | ".join(str(int(table.loc[decision, col])) for col in columns)
        lines.append(f"| {decision} | {cells} |")
    return "\n".join(lines)


def format_proportions_table(
    table: pd.DataFrame, decision_rows: tuple[str, ...], decimals: int
) -> str:
    """Format a proportion crosstab as a markdown pipe table.

    Parameters
    ----------
    table
        Float proportion crosstab indexed by decision rows.
    decision_rows
        Row order for the markdown table.
    decimals
        Fixed decimal places for each proportion cell.

    Returns
    -------
    str
        Markdown pipe table with fixed-decimal proportion cells.
    """
    columns = list(table.columns)
    header = "| decision | " + " | ".join(columns) + " |"
    separator = "|---|" + "|".join(["---:"] * len(columns)) + "|"
    lines = [header, separator]
    for decision in decision_rows:
        cells = " | ".join(
            f"{float(table.loc[decision, col]):.{decimals}f}" for col in columns
        )
        lines.append(f"| {decision} | {cells} |")
    return "\n".join(lines)


def format_four_cell_table(
    cell_counts: pd.DataFrame, cell_shares: pd.DataFrame
) -> str:
    """Format the four-cell count and share table.

    Parameters
    ----------
    cell_counts
        Frame with ``cell`` and ``count`` columns.
    cell_shares
        Frame with ``cell`` and ``share`` columns.

    Returns
    -------
    str
        Markdown table with header ``| cell | count | share |``.
    """
    merged = cell_counts.merge(cell_shares[["cell", "share"]], on="cell")
    lines = ["| cell | count | share |", "|---|---:|---:|"]
    for _, row in merged.iterrows():
        share_text = f"{float(row['share']):.{PROPORTION_DECIMALS}f}"
        lines.append(f"| {row['cell']} | {int(row['count'])} | {share_text} |")
    return "\n".join(lines)


def format_funnel_table(funnel: pd.DataFrame) -> str:
    """Format the vote funnel metric table.

    Parameters
    ----------
    funnel
        Frame with ``metric`` and ``count`` columns.

    Returns
    -------
    str
        Markdown table with header ``| metric | count |``.
    """
    lines = ["| metric | count |", "|---|---:|"]
    for _, row in funnel.iterrows():
        lines.append(f"| {row['metric']} | {int(row['count'])} |")
    return "\n".join(lines)


def format_results_markdown(
    platform_counts: pd.DataFrame,
    platform_proportions: pd.DataFrame,
    platform_toxicity_proportions: pd.DataFrame,
    four_cell_counts: pd.DataFrame,
    four_cell_shares: pd.DataFrame,
    funnel: pd.DataFrame,
) -> str:
    """Render the full RESULTS.md body with section headings."""
    raise NotImplementedError


def write_results(
    markdown: str,
    csv_bundle: dict[str, pd.DataFrame],
    experiment_dir: Path,
) -> Path:
    """Write RESULTS.md and CSV files under ``experiment_dir / outputs``."""
    raise NotImplementedError
