"""Write count tables, the results file, and S3 copies.

Run from the repo root::

    PYTHONPATH=. uv run python experiments/compare_jev_human_uncertainty_2026_09_25/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    DIFFERENCE_SCORE_MAX,
    DIFFERENCE_SCORE_MIN,
    EXPECTED_FIVE_LABELER_POSTS,
    EXPECTED_JEV_BIN_COUNTS,
    EXPECTED_MEAN_DIFFERENCE,
    EXPECTED_REMOVE_COUNTS,
    JEV_BIN_COUNT,
    REQUIRED_LABELERS,
    TABLE_FILENAMES,
)
from lib.aws.s3 import DEFAULT_REGION_NAME, S3
from lib.constants import REPO_ROOT

_NO_SKIP_SENTENCE = (
    "Moderation trials have no skip decision. "
    "The human count is the number of remove votes among five labelers."
)
_FIGURE_LINKS = (
    ("Human remove counts", "outputs/figures/human_remove_counts.png"),
    ("Jev probability", "outputs/figures/jev_probability.png"),
    ("Jev six bins", "outputs/figures/jev_six_bins.png"),
    ("Human counts and Jev bins", "outputs/figures/overlay_human_vs_jev.png"),
    ("Difference score", "outputs/figures/difference_score.png"),
)


def _count_tuple(series: pd.Series, keys: range) -> tuple[int, ...]:
    """Return post counts for each key, using 0 when a key is absent."""
    counts = series.value_counts()
    return tuple(int(counts.get(key, 0)) for key in keys)


def _count_frame(series: pd.Series, column: str, keys: range) -> pd.DataFrame:
    """Return a two-column count table for ``keys``."""
    counts = series.value_counts()
    return pd.DataFrame(
        {
            column: list(keys),
            "n_posts": [int(counts.get(key, 0)) for key in keys],
        }
    )


def _require_comparison_rows(frame: pd.DataFrame) -> None:
    """Raise ValueError when the joined row count is not pinned."""
    if len(frame) != EXPECTED_FIVE_LABELER_POSTS:
        raise ValueError(
            f"expected {EXPECTED_FIVE_LABELER_POSTS} rows, found {len(frame)}"
        )


def _require_remove_counts(frame: pd.DataFrame) -> None:
    """Raise ValueError when remove-vote counts differ from the pin."""
    observed = _count_tuple(frame["n_remove"], range(REQUIRED_LABELERS + 1))
    if observed != EXPECTED_REMOVE_COUNTS:
        raise ValueError(f"remove counts {observed}")


def _require_jev_bin_counts(frame: pd.DataFrame) -> None:
    """Raise ValueError when Jev bin counts differ from the pin."""
    observed = _count_tuple(frame["jev_bin"], range(JEV_BIN_COUNT))
    if observed != EXPECTED_JEV_BIN_COUNTS:
        raise ValueError(f"Jev bin counts {observed}")


def _require_mean_difference(frame: pd.DataFrame) -> None:
    """Raise ValueError when the rounded mean difference differs from the pin."""
    observed = f"{float(frame['difference_score'].mean()):.4f}"
    expected = f"{EXPECTED_MEAN_DIFFERENCE:.4f}"
    if observed != expected:
        raise ValueError(f"mean difference {observed}")


def assert_pinned_counts(frame: pd.DataFrame) -> None:
    """Raise ValueError when a pinned count or the rounded mean differs.

    Parameters
    ----------
    frame
        Comparison rows with ``n_remove``, ``jev_bin``, and ``difference_score``.
    """
    _require_comparison_rows(frame)
    _require_remove_counts(frame)
    _require_jev_bin_counts(frame)
    _require_mean_difference(frame)


def _crosstab(frame: pd.DataFrame) -> pd.DataFrame:
    """Return remove-count rows by Jev bin, including empty cells as 0."""
    table = pd.crosstab(frame["n_remove"], frame["jev_bin"])
    filled = table.reindex(
        index=list(range(REQUIRED_LABELERS + 1)),
        columns=list(range(JEV_BIN_COUNT)),
        fill_value=0,
    )
    filled.index.name = "n_remove"
    return filled.reset_index()


def write_count_tables(
    frame: pd.DataFrame, table_dir: Path
) -> tuple[Path, Path, Path, Path]:
    """Write the four count CSVs.

    Returns
    -------
    tuple
        Paths for human counts, Jev bins, difference scores, and the crosstab.
    """
    table_dir.mkdir(parents=True, exist_ok=True)
    human_keys = range(REQUIRED_LABELERS + 1)
    jev_keys = range(JEV_BIN_COUNT)
    difference_keys = range(DIFFERENCE_SCORE_MIN, DIFFERENCE_SCORE_MAX + 1)
    tables = (
        _count_frame(frame["n_remove"], "n_remove", human_keys),
        _count_frame(frame["jev_bin"], "jev_bin", jev_keys),
        _count_frame(frame["difference_score"], "difference_score", difference_keys),
        _crosstab(frame),
    )
    paths: list[Path] = []
    for table, name in zip(tables, TABLE_FILENAMES, strict=True):
        path = table_dir / name
        table.to_csv(path, index=False)
        paths.append(path)
    return (paths[0], paths[1], paths[2], paths[3])


def _markdown_table(frame: pd.DataFrame) -> str:
    """Return a GitHub-flavored table for ``frame``."""
    headers = [str(column) for column in frame.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in frame.itertuples(index=False):
        cells = [str(value) for value in row]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def _figure_lines() -> list[str]:
    """Return markdown image lines for the five figures."""
    lines: list[str] = []
    for title, path in _FIGURE_LINKS:
        lines.extend([f"![{title}]({path})", ""])
    return lines


def _table_lines(frame: pd.DataFrame) -> list[str]:
    """Return markdown headings and tables for the four count tables."""
    human_keys = range(REQUIRED_LABELERS + 1)
    jev_keys = range(JEV_BIN_COUNT)
    difference_keys = range(DIFFERENCE_SCORE_MIN, DIFFERENCE_SCORE_MAX + 1)
    labeled = (
        ("Human remove counts", _count_frame(frame["n_remove"], "n_remove", human_keys)),
        ("Jev probability bins", _count_frame(frame["jev_bin"], "jev_bin", jev_keys)),
        (
            "Difference scores",
            _count_frame(frame["difference_score"], "difference_score", difference_keys),
        ),
        ("Remove votes by Jev bin", _crosstab(frame)),
    )
    lines: list[str] = []
    for title, table in labeled:
        lines.extend([f"## {title}", "", _markdown_table(table), ""])
    return lines


def _bin_sentence() -> str:
    """Return the sentence that maps the six Jev bins onto remove counts."""
    last_bin = JEV_BIN_COUNT - 1
    return (
        f"Jev probabilities are split into {JEV_BIN_COUNT} equal bins from 0 to 1. "
        f"Bin 0 matches 0 remove votes, and bin {last_bin} matches "
        f"{REQUIRED_LABELERS} remove votes."
    )


def _results_sections(frame: pd.DataFrame) -> list[str]:
    """Return the RESULTS.md sections for ``frame``."""
    mean = f"{float(frame['difference_score'].mean()):.4f}"
    return [
        "# Jev probabilities and human remove counts",
        "",
        _NO_SKIP_SENTENCE,
        "",
        _bin_sentence(),
        "",
        f"The mean difference score, human remove count minus Jev bin, is {mean}.",
        "",
        *_figure_lines(),
        *_table_lines(frame),
    ]


def write_results(frame: pd.DataFrame, results_path: Path) -> Path:
    """Write RESULTS.md from the counts in ``frame``.

    Returns
    -------
    pathlib.Path
        The markdown path.
    """
    results_path.parent.mkdir(parents=True, exist_ok=True)
    results_path.write_text("\n".join(_results_sections(frame)) + "\n", encoding="utf-8")
    return results_path


def upload_outputs(paths: tuple[Path, ...], bucket: str) -> None:
    """Upload each path using the repo-relative POSIX key.

    Parameters
    ----------
    paths
        Local files to upload.
    bucket
        Destination bucket name.
    """
    store = S3(bucket, region_name=DEFAULT_REGION_NAME)
    for path in paths:
        key = path.resolve().relative_to(REPO_ROOT).as_posix()
        store.upload_file(path, key)
