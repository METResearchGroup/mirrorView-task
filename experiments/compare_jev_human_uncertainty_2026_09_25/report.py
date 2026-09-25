"""Write count tables, the results file, and S3 copies.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_report.py -q
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def assert_pinned_counts(frame: pd.DataFrame) -> None:
    raise NotImplementedError


def write_count_tables(frame: pd.DataFrame, table_dir: Path) -> tuple[Path, Path, Path, Path]:
    raise NotImplementedError


def write_results(frame: pd.DataFrame, results_path: Path) -> Path:
    raise NotImplementedError


def upload_outputs(paths: tuple[Path, ...], bucket: str) -> None:
    raise NotImplementedError
