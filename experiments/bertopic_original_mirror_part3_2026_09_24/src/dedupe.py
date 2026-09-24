"""Dedupe Part 3 stimuli before topic fitting.

Run from repo root::

    PYTHONPATH=. uv run python -c \\
      "from experiments.bertopic_original_mirror_part3_2026_09_24.src.dedupe import dedupe_stimuli"
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def dedupe_stimuli(stimuli: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    raise NotImplementedError


def build_dedupe_report(
    before: pd.DataFrame,
    after: pd.DataFrame,
    removed_dup_orig: int,
    removed_identical: int,
) -> dict:
    raise NotImplementedError


def write_dedupe_report(path: Path, report: dict) -> None:
    raise NotImplementedError
