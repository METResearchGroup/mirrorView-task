"""Split Study 2 modal keep/remove labels by five-labeler agreement.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_2/split_keep_remove_labels.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

UNANIMOUS_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_unanimous_labels.csv"
SPLIT_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_split_labels.csv"


def select_five_rater_labels(labels):
    """Return posts with exactly five labelers."""
    raise NotImplementedError


def build_unanimous_keep_remove_labels(labels=None):
    """Return five-labeler posts with 0 or 5 remove votes."""
    raise NotImplementedError


def build_split_keep_remove_labels(labels=None):
    """Return five-labeler posts with 1, 2, 3, or 4 remove votes."""
    raise NotImplementedError


def _load_modal_labels(labels):
    """Load ``STUDY_2_KEEP_REMOVE_LABELS`` when ``labels`` is omitted."""
    raise NotImplementedError


def _write_label_frame(frame, path):
    """Write ``frame`` to ``path`` and return it."""
    raise NotImplementedError


def write_keep_remove_label_splits(
    labels=None,
    unanimous_path=UNANIMOUS_OUTPUT_CSV,
    split_path=SPLIT_OUTPUT_CSV,
):
    """Load modal labels, split five-labeler posts, and write both CSVs.

    Shape: load modal labels, build unanimous rows, build split rows, write both.
    """
    raise NotImplementedError


if __name__ == "__main__":
    unanimous, split = write_keep_remove_label_splits()
    print(f"Wrote {UNANIMOUS_OUTPUT_CSV} rows={len(unanimous)}")
    print(f"Wrote {SPLIT_OUTPUT_CSV} rows={len(split)}")
