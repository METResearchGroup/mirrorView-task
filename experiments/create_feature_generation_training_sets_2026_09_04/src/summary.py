"""Collect local parquet stats and render SUMMARY.md for the training-set experiment.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/create_feature_generation_training_sets_2026_09_04/main.py --upload
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
    S3_BUCKET,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.paths import (
    experiment_root,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.upload import (
    s3_key_for,
)

BYTES_PER_MB = 1_000_000
SUMMARY_FILENAME = "SUMMARY.md"
FILE_TABLE_HEADER = "| file | size_mb | n_rows | s3_prefix |"
FILE_TABLE_SEPARATOR = "| --- | --- | --- | --- |"
TOTALS_TABLE_HEADER = "| category | n_rows |"
TOTALS_TABLE_SEPARATOR = "| --- | --- |"
TOTALS_SECTION_HEADING = "## Totals"


@dataclass(frozen=True)
class FileStat:
    """One uploaded training parquet and its local metadata."""

    classifier_name: str
    file: str
    size_mb: float
    n_rows: int
    s3_prefix: str


def collect_file_stats(paths: list[Path], output_root: Path) -> list[FileStat]:
    """Collect row counts, sizes, and S3 keys for local training parquets.

    Parameters
    ----------
    paths
        Local parquet paths produced by :func:`build_training_sets`.
    output_root
        Local root used to derive classifier folders and object keys.

    Returns
    -------
    list[FileStat]
        One stat record per parquet path, in input order.
    """
    stats: list[FileStat] = []

    for local_path in paths:
        if local_path.name == ".gitkeep":
            continue

        classifier_name = local_path.relative_to(output_root).parts[0]
        size_mb = round(local_path.stat().st_size / BYTES_PER_MB, 2)
        n_rows = len(pd.read_parquet(local_path))
        stats.append(
            FileStat(
                classifier_name=classifier_name,
                file=local_path.name,
                size_mb=size_mb,
                n_rows=n_rows,
                s3_prefix=s3_key_for(local_path, output_root),
            )
        )

    return stats


def _classifier_row_totals(stats: list[FileStat]) -> dict[str, int]:
    totals = {classifier_name: 0 for classifier_name in CLASSIFIER_NAMES}
    for stat in stats:
        totals[stat.classifier_name] = totals.get(stat.classifier_name, 0) + stat.n_rows
    return totals


def _render_classifier_table(classifier_stats: list[FileStat]) -> str:
    if not classifier_stats:
        return f"{FILE_TABLE_HEADER}\n{FILE_TABLE_SEPARATOR}\n"

    rows = [
        f"| {stat.file} | {stat.size_mb} | {stat.n_rows} | {stat.s3_prefix} |"
        for stat in classifier_stats
    ]
    return "\n".join([FILE_TABLE_HEADER, FILE_TABLE_SEPARATOR, *rows, ""])


def render_summary_markdown(stats: list[FileStat]) -> str:
    """Render SUMMARY.md content from collected file stats.

    Parameters
    ----------
    stats
        File stats for every uploaded parquet.

    Returns
    -------
    str
        Markdown with one table per classifier and a final totals table.
    """
    stats_by_classifier: dict[str, list[FileStat]] = {
        classifier_name: [] for classifier_name in CLASSIFIER_NAMES
    }
    for stat in stats:
        stats_by_classifier[stat.classifier_name].append(stat)

    sections = [
        f"Training parquets were uploaded to S3 bucket `{S3_BUCKET}`.",
        "",
    ]

    for classifier_name in CLASSIFIER_NAMES:
        sections.append(f"## {classifier_name}")
        sections.append("")
        sections.append(_render_classifier_table(stats_by_classifier[classifier_name]))

    row_totals = _classifier_row_totals(stats)
    totals_rows = [
        f"| {classifier_name} | {row_totals[classifier_name]} |"
        for classifier_name in CLASSIFIER_NAMES
    ]
    sections.extend(
        [
            TOTALS_SECTION_HEADING,
            "",
            TOTALS_TABLE_HEADER,
            TOTALS_TABLE_SEPARATOR,
            *totals_rows,
            "",
        ]
    )
    return "\n".join(sections)


def write_summary(stats: list[FileStat], path: Path | None = None) -> Path:
    """Write SUMMARY.md for the experiment.

    Parameters
    ----------
    stats
        File stats for every uploaded parquet.
    path
        Destination markdown path; defaults to ``experiment_root() / SUMMARY.md``.

    Returns
    -------
    Path
        Path written on disk.
    """
    summary_path = path if path is not None else experiment_root() / SUMMARY_FILENAME
    summary_path.write_text(render_summary_markdown(stats), encoding="utf-8")
    return summary_path
