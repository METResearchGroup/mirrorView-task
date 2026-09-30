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


def _require_columns(labels: pd.DataFrame) -> None:
    """Raise KeyError when ``n_raters`` or ``n_remove`` is missing."""
    missing = REQUIRED_COLUMNS - set(labels.columns)
    if missing:
        raise KeyError(f"Dataset is missing required columns: {sorted(missing)}")


def _integer_column(labels: pd.DataFrame, column: str) -> pd.Series:
    """Return ``column`` as integers, or raise when a value is not integral."""
    numeric = pd.to_numeric(labels[column], errors="coerce")
    non_integer = numeric.isna() | (numeric != numeric.round())
    if bool(non_integer.any()):
        raise ValueError(f"{column} must be an integer on every row")
    return numeric.astype(int)


def _assert_five_rater_remove_counts(n_remove: pd.Series) -> None:
    """Raise when a five-labeler remove count is outside 0 to 5."""
    allowed = UNANIMOUS_REMOVE_COUNTS | SPLIT_REMOVE_COUNTS
    unexpected = sorted(set(int(value) for value in n_remove.tolist()) - allowed)
    if unexpected:
        raise ValueError(
            "Five-labeler posts must have n_remove from 0 to 5. "
            f"Unexpected n_remove values: {unexpected}."
        )


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
    _require_columns(labels)
    n_raters = _integer_column(labels, "n_raters")
    n_remove = _integer_column(labels, "n_remove")
    five_rater = n_raters == FIVE_LABELER_COUNT
    _assert_five_rater_remove_counts(n_remove.loc[five_rater])
    return labels.loc[five_rater].reset_index(drop=True)


def _rows_with_remove_counts(
    labels: pd.DataFrame,
    remove_counts: frozenset[int],
) -> pd.DataFrame:
    """Return five-labeler rows whose remove count is in ``remove_counts``."""
    five_rater = select_five_rater_labels(labels)
    n_remove = _integer_column(five_rater, "n_remove")
    selected = five_rater.loc[n_remove.isin(remove_counts)]
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
    modal = labels if labels is not None else _load_modal_labels(None)
    return _rows_with_remove_counts(modal, UNANIMOUS_REMOVE_COUNTS)


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
    modal = labels if labels is not None else _load_modal_labels(None)
    return _rows_with_remove_counts(modal, SPLIT_REMOVE_COUNTS)


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
