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
from shared.data.transformed.keep_remove_aggregation import (
    aggregate_modal_labels,
    filter_keep_remove_trials,
)

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
    """Build modal keep/remove labels from Part 3 results.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Part 3 results. When omitted, loads
        ``STUDY_PHASE_2_PART_3_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``message_id``, ``original_text``,
        ``mirror_text``, ``decision``, ``keep_remove_label``, and ``n_raters``.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_3_RESULTS_FULL, low_memory=False)
    trials = filter_keep_remove_trials(raw, dedupe_worker_post=True)
    labels = aggregate_modal_labels(trials)
    return labels[_OUTPUT_COLUMNS].reset_index(drop=True)


def write_keep_remove_labels(path: Path = OUTPUT_CSV) -> pd.DataFrame:
    """Write modal keep/remove labels to CSV and return the frame.

    Parameters
    ----------
    path : pathlib.Path, optional
        Destination CSV path.

    Returns
    -------
    pandas.DataFrame
        The same frame written to disk.
    """
    df = build_keep_remove_labels()
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return df


if __name__ == "__main__":
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")
