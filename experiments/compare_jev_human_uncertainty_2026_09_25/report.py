"""Write count tables, the results file, and S3 copies.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_report.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def assert_pinned_counts(frame: pd.DataFrame) -> None:
    """Raise ValueError when a pinned count or the rounded mean differs.

    Parameters
    ----------
    frame
        Comparison rows with ``n_remove``, ``jev_bin``, and ``difference_score``.
    """
    raise NotImplementedError


def write_count_tables(frame: pd.DataFrame, table_dir: Path) -> tuple[Path, Path, Path, Path]:
    """Write the four count CSVs.

    Returns
    -------
    tuple
        Paths for human counts, Jev bins, difference scores, and the crosstab.
    """
    raise NotImplementedError


def write_results(frame: pd.DataFrame, results_path: Path) -> Path:
    """Write RESULTS.md from the counts in ``frame``.

    Returns
    -------
    pathlib.Path
        The markdown path.
    """
    raise NotImplementedError


def upload_outputs(paths: tuple[Path, ...], bucket: str) -> None:
    """Upload each path using the repo-relative POSIX key.

    Parameters
    ----------
    paths
        Local files to upload.
    bucket
        Destination bucket name.
    """
    raise NotImplementedError
