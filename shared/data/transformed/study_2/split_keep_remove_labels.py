"""Split Study 2 modal keep/remove labels by five-labeler agreement.

Posts with any other labeler count stay out of both subsets. Unanimous posts
have 0 or 5 remove votes. Split posts have 1, 2, 3, or 4 remove votes.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_2/split_keep_remove_labels.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from shared.data import dataloader
from shared.data.registry import STUDY_2_KEEP_REMOVE_LABELS

FIVE_LABELER_COUNT = 5
UNANIMOUS_REMOVE_COUNTS = frozenset({0, FIVE_LABELER_COUNT})
SPLIT_REMOVE_COUNTS = frozenset(range(1, FIVE_LABELER_COUNT))

UNANIMOUS_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_unanimous_labels.csv"
SPLIT_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_split_labels.csv"


def _five_labeler_subset(
    labels: pd.DataFrame,
    remove_counts: frozenset[int],
) -> pd.DataFrame:
    """Return five-labeler rows whose remove count is in ``remove_counts``.

    Raises
    ------
    KeyError
        When ``n_raters`` or ``n_remove`` is missing.
    """
    five_labelers = labels.loc[labels["n_raters"] == FIVE_LABELER_COUNT]
    selected = five_labelers.loc[five_labelers["n_remove"].isin(remove_counts)]
    return selected.reset_index(drop=True)


def build_unanimous_keep_remove_labels(
    labels: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return five-labeler posts with 0 or 5 remove votes.

    Parameters
    ----------
    labels
        Modal keep/remove rows. Loads ``STUDY_2_KEEP_REMOVE_LABELS`` when omitted.

    Returns
    -------
    pandas.DataFrame
        Unanimous five-labeler rows. Other labeler counts are excluded.
    """
    return _five_labeler_subset(_load_modal_labels(labels), UNANIMOUS_REMOVE_COUNTS)


def build_split_keep_remove_labels(
    labels: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Return five-labeler posts with 1, 2, 3, or 4 remove votes.

    Parameters
    ----------
    labels
        Modal keep/remove rows. Loads ``STUDY_2_KEEP_REMOVE_LABELS`` when omitted.

    Returns
    -------
    pandas.DataFrame
        Split five-labeler rows. Other labeler counts are excluded.
    """
    return _five_labeler_subset(_load_modal_labels(labels), SPLIT_REMOVE_COUNTS)


def _load_modal_labels(labels: pd.DataFrame | None) -> pd.DataFrame:
    """Return ``labels`` or load ``STUDY_2_KEEP_REMOVE_LABELS``."""
    if labels is not None:
        return labels
    return dataloader.load_dataset(STUDY_2_KEEP_REMOVE_LABELS, low_memory=False)


def write_keep_remove_label_splits(
    labels: pd.DataFrame | None = None,
    unanimous_path: Path = UNANIMOUS_OUTPUT_CSV,
    split_path: Path = SPLIT_OUTPUT_CSV,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Write unanimous and split five-labeler CSVs.

    Parameters
    ----------
    labels
        Modal keep/remove rows. Loads ``STUDY_2_KEEP_REMOVE_LABELS`` when omitted.
    unanimous_path
        Destination for posts with 0 or 5 remove votes.
    split_path
        Destination for posts with 1, 2, 3, or 4 remove votes.

    Returns
    -------
    tuple[pandas.DataFrame, pandas.DataFrame]
        Unanimous frame, then split frame.
    """
    modal = _load_modal_labels(labels)
    unanimous = build_unanimous_keep_remove_labels(modal)
    split = build_split_keep_remove_labels(modal)
    unanimous_path.parent.mkdir(parents=True, exist_ok=True)
    split_path.parent.mkdir(parents=True, exist_ok=True)
    unanimous.to_csv(unanimous_path, index=False)
    split.to_csv(split_path, index=False)
    return unanimous, split


if __name__ == "__main__":
    unanimous, split = write_keep_remove_label_splits()
    print(f"Wrote {UNANIMOUS_OUTPUT_CSV} rows={len(unanimous)}")
    print(f"Wrote {SPLIT_OUTPUT_CSV} rows={len(split)}")
