"""Format and write RESULTS.md and output CSV mirrors.

Run from repo root::

    PYTHONPATH=. uv run python experiments/phase_2_part_3_keep_remove_descriptive_stats_2026_09_24/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def format_counts_table(
    table: pd.DataFrame, decision_rows: tuple[str, ...]
) -> str:
    """Format an integer crosstab as a markdown pipe table."""
    raise NotImplementedError


def format_proportions_table(
    table: pd.DataFrame, decision_rows: tuple[str, ...], decimals: int
) -> str:
    """Format a proportion crosstab as a markdown pipe table."""
    raise NotImplementedError


def format_four_cell_table(
    cell_counts: pd.DataFrame, cell_shares: pd.DataFrame
) -> str:
    """Format the four-cell count and share table."""
    raise NotImplementedError


def format_funnel_table(funnel: pd.DataFrame) -> str:
    """Format the vote funnel metric table."""
    raise NotImplementedError


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
