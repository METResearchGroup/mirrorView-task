"""Build and materialize Part 3 keep/remove training labels.

Public entrypoints:

- ``build_keep_remove_labels`` / ``write_keep_remove_labels`` →
  ``keep_remove_labels.csv``

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_phase_2_part_3/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_3_RESULTS_FULL

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = OUTPUT_DIR / "keep_remove_labels.csv"

_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
]


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build modal keep/remove labels from Part 3 results."""
    raise NotImplementedError


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write modal keep/remove labels to CSV and return the frame."""
    raise NotImplementedError


if __name__ == "__main__":
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")
