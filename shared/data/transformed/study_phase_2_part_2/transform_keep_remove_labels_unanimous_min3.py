"""Build and materialize Part 2 unanimous min-3 keep/remove labels.

Public entrypoints:

- ``build_keep_remove_labels_unanimous_min3`` /
  ``write_keep_remove_labels_unanimous_min3`` →
  ``keep_remove_labels_unanimous_min3.csv``

Inclusion rule: linked-fate keep/remove trials with usable ``post_id``,
grouped by post; keep posts with ``n_raters >= 3`` where all raters share
the same decision (unanimous).

Run from repo root::

    PYTHONPATH=. uv run python \\
      shared/data/transformed/study_phase_2_part_2/transform_keep_remove_labels_unanimous_min3.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_RESULTS_FULL
from shared.data.transformed.keep_remove_aggregation import (
    aggregate_unanimous_labels,
    filter_keep_remove_trials,
)

OUTPUT_DIR = Path(__file__).resolve().parent
OUTPUT_CSV = OUTPUT_DIR / "keep_remove_labels_unanimous_min3.csv"

_MIN_RATERS = 3
_OUTPUT_COLUMNS = [
    "message_id",
    "original_text",
    "mirror_text",
    "decision",
    "keep_remove_label",
    "n_raters",
]


def build_keep_remove_labels_unanimous_min3(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build unanimous min-3 keep/remove labels from Part 2 results.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Part 2 results. When omitted, loads
        ``STUDY_PHASE_2_PART_2_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``message_id``, ``original_text``,
        ``mirror_text``, ``decision``, ``keep_remove_label``, and ``n_raters``.

    Raises
    ------
    KeyError
        If required columns are missing from the source frame.
    ValueError
        If a post has conflicting original or mirror text across trials.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_2_RESULTS_FULL, low_memory=False)
    trials = filter_keep_remove_trials(raw, dedupe_worker_post=False)
    labels = aggregate_unanimous_labels(trials, min_raters=_MIN_RATERS)
    return labels[_OUTPUT_COLUMNS].reset_index(drop=True)


def write_keep_remove_labels_unanimous_min3(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write unanimous min-3 keep/remove labels to CSV and return the frame.

    Creates parent directories as needed. By default writes
    ``keep_remove_labels_unanimous_min3.csv`` next to this script.

    Parameters
    ----------
    path : pathlib.Path, optional
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        The same frame written to disk.
    """
    df = build_keep_remove_labels_unanimous_min3()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    labels = write_keep_remove_labels_unanimous_min3()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")
