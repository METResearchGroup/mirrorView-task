"""Build and materialize Part 2 and Part 3 union keep/remove training labels.

Public entrypoints:

- ``build_keep_remove_labels`` / ``write_keep_remove_labels`` →
  ``keep_remove_labels.csv``

Run from repo root::

    PYTHONPATH=. uv run python \\
      shared/data/transformed/study_phase_2_part_2_and_3/transform.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL
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


def _dedupe_diagnostics(raw: pd.DataFrame) -> tuple[int, int, int]:
    """Return conflicting pair count, pre-dedupe rows, post-dedupe rows."""
    before_dedupe = filter_keep_remove_trials(raw, dedupe_worker_post=False)
    after_dedupe = filter_keep_remove_trials(raw, dedupe_worker_post=True)
    pair_decisions = (
        before_dedupe.groupby(["prolific_id", "post_id"], dropna=False)["decision"]
        .nunique()
        .reset_index(name="n_unique_decisions")
    )
    conflicting_pairs = int((pair_decisions["n_unique_decisions"] > 1).sum())
    return conflicting_pairs, len(before_dedupe), len(after_dedupe)


def build_keep_remove_labels(
    raw: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build modal keep/remove labels from the Part 2 and Part 3 union results.

    Parameters
    ----------
    raw : pandas.DataFrame, optional
        Combined Part 2 and Part 3 results. When omitted, loads
        ``STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL`` via the shared dataloader.

    Returns
    -------
    pandas.DataFrame
        One row per post with ``message_id``, ``original_text``,
        ``mirror_text``, ``decision``, ``keep_remove_label``, and ``n_raters``.
    """
    if raw is None:
        raw = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
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
    raw = load_dataset(STUDY_PHASE_2_PART_2_AND_3_RESULTS_FULL, low_memory=False)
    conflicting_pairs, before_dedupe, after_dedupe = _dedupe_diagnostics(raw)
    print(f"conflicting_worker_post_pairs={conflicting_pairs}")
    print(f"rows_dropped_by_dedupe={before_dedupe - after_dedupe}")
    print(f"trial_rows_after_dedupe={after_dedupe}")
    labels = write_keep_remove_labels()
    print(f"Wrote {OUTPUT_CSV}")
    print(f"rows={len(labels)}")
    print(labels["decision"].value_counts().to_dict())
    print(f"columns={list(labels.columns)}")
