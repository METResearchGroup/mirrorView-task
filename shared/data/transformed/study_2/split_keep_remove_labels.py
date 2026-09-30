"""Split Study 2 modal keep/remove labels by five-labeler agreement.

Posts with any other labeler count stay out of both subsets. Unanimous posts
have 0 or 5 remove votes. Split posts have 1, 2, 3, or 4 remove votes.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_2/split_keep_remove_labels.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

FIVE_LABELER_COUNT = 5
UNANIMOUS_REMOVE_COUNTS = frozenset({0, FIVE_LABELER_COUNT})
SPLIT_REMOVE_COUNTS = frozenset(range(1, FIVE_LABELER_COUNT))
REQUIRED_COLUMNS = frozenset({"n_raters", "n_remove"})

UNANIMOUS_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_unanimous_labels.csv"
SPLIT_OUTPUT_CSV = Path(__file__).resolve().parent / "keep_remove_split_labels.csv"


def select_five_rater_labels(labels: pd.DataFrame) -> pd.DataFrame:
    """Return posts that have exactly five labelers.

    Parameters
    ----------
    labels
        Modal keep/remove rows, including ``n_raters`` and ``n_remove``.

    Returns
    -------
    pandas.DataFrame
        Copy of the five-labeler rows, with the input columns unchanged.

    Raises
    ------
    KeyError
        When ``n_raters`` or ``n_remove`` is missing.
    ValueError
        When a count is not an integer, or a five-labeler post has
        ``n_remove`` outside 0 to 5.
    """
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


def _load_modal_labels(labels: pd.DataFrame | None) -> pd.DataFrame:
    """Return ``labels`` or load ``STUDY_2_KEEP_REMOVE_LABELS``."""
    raise NotImplementedError


def _write_label_frame(frame: pd.DataFrame, path: Path) -> pd.DataFrame:
    """Write ``frame`` to ``path`` and return it."""
    raise NotImplementedError


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
    raise NotImplementedError


if __name__ == "__main__":
    unanimous, split = write_keep_remove_label_splits()
    print(f"Wrote {UNANIMOUS_OUTPUT_CSV} rows={len(unanimous)}")
    print(f"Wrote {SPLIT_OUTPUT_CSV} rows={len(split)}")
