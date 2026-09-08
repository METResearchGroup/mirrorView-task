"""Compute remaining labels for old and new stimulus posts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import pandas as pd

from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.constants import (
    Batch,
    EMPTY_CELL,
    NAN_CELL,
    NEW_ID_COLUMN,
    OLD_ID_COLUMN,
    OUTPUT_BATCH_COLUMN,
    OUTPUT_COUNT_COLUMN,
    OUTPUT_ID_COLUMN,
    RATER_COLUMN,
    RESULTS_ID_COLUMN,
    SORT_KIND,
)

OLD_BATCH_SORT_RANK = 0
NEW_BATCH_SORT_RANK = 1
BATCH_SORT_RANK = {
    Batch.OLD.value: OLD_BATCH_SORT_RANK,
    Batch.NEW.value: NEW_BATCH_SORT_RANK,
}
KEEP_REMAINING_ABOVE = 0
BATCH_RANK_COLUMN = "_batch_rank"


def count_unique_raters_per_post(old_results: pd.DataFrame) -> pd.Series:
    """Count unique ``prolific_id`` raters for each ``post_id``.

    Parameters
    ----------
    old_results
        Study results with ``post_id`` and ``prolific_id``.

    Returns
    -------
    pd.Series
        Unique rater counts indexed by ``post_id``.
    """
    rows = _usable_rater_rows(old_results)
    counts = rows.groupby(RESULTS_ID_COLUMN, sort=False)[RATER_COLUMN].nunique()
    counts.name = RATER_COLUMN
    return counts


def remaining_labels_for_old_posts(
    old_catalog: pd.DataFrame,
    rater_counts: pd.Series,
    required_labels_per_post: int,
) -> pd.DataFrame:
    """Return remaining labels for each old catalog post.

    Parameters
    ----------
    old_catalog
        Catalog rows with unique ``post_primary_key`` values.
    rater_counts
        Unique rater counts indexed by ``post_id``.
    required_labels_per_post
        Target label count per post.

    Returns
    -------
    pd.DataFrame
        Columns ``id``, ``number_of_times_to_label``, and ``batch``.
    """
    ids = old_catalog[OLD_ID_COLUMN]
    unique_raters = ids.map(rater_counts).fillna(0).astype(int)
    remaining = required_labels_per_post - unique_raters
    return pd.DataFrame(
        {
            OUTPUT_ID_COLUMN: ids.to_numpy(),
            OUTPUT_COUNT_COLUMN: remaining.to_numpy(),
            OUTPUT_BATCH_COLUMN: Batch.OLD.value,
        }
    )


def remaining_labels_for_new_posts(
    new_sample: pd.DataFrame,
    required_labels_per_post: int,
) -> pd.DataFrame:
    """Return remaining labels for each new sample post.

    Parameters
    ----------
    new_sample
        New sample rows with unique ``record_id`` values.
    required_labels_per_post
        Target label count per post.

    Returns
    -------
    pd.DataFrame
        Columns ``id``, ``number_of_times_to_label``, and ``batch``.
    """
    ids = new_sample[NEW_ID_COLUMN].astype(str).str.strip()
    return pd.DataFrame(
        {
            OUTPUT_ID_COLUMN: ids.to_numpy(),
            OUTPUT_COUNT_COLUMN: required_labels_per_post,
            OUTPUT_BATCH_COLUMN: Batch.NEW.value,
        }
    )


def combine_and_filter_batches(
    old_counts: pd.DataFrame,
    new_counts: pd.DataFrame,
) -> pd.DataFrame:
    """Concatenate batches, fail on overlapping ids, and drop remaining counts of 0 or less.

    Parameters
    ----------
    old_counts
        Remaining-label rows for the old batch.
    new_counts
        Remaining-label rows for the new batch.

    Returns
    -------
    pd.DataFrame
        Sorted remaining-label rows with ``number_of_times_to_label`` greater than 0.

    Raises
    ------
    ValueError
        When the same id appears in both batches.
    """
    _require_no_id_overlap(old_counts[OUTPUT_ID_COLUMN], new_counts[OUTPUT_ID_COLUMN])
    combined = pd.concat([old_counts, new_counts], ignore_index=True)
    remaining = combined[combined[OUTPUT_COUNT_COLUMN] > KEEP_REMAINING_ABOVE].copy()
    return _sort_remaining_rows(remaining)


def calculate_required_label_counts(
    old_catalog: pd.DataFrame,
    old_results: pd.DataFrame,
    new_sample: pd.DataFrame,
    required_labels_per_post: int,
) -> pd.DataFrame:
    """Return remaining label counts for old and new posts.

    Parameters
    ----------
    old_catalog
        Old stimulus catalog.
    old_results
        Old study results.
    new_sample
        New sample parquet.
    required_labels_per_post
        Target label count per post.

    Returns
    -------
    pd.DataFrame
        Remaining-label table sorted by batch then id.
    """
    rater_counts = count_unique_raters_per_post(old_results)
    old_counts = remaining_labels_for_old_posts(
        old_catalog, rater_counts, required_labels_per_post
    )
    new_counts = remaining_labels_for_new_posts(new_sample, required_labels_per_post)
    return combine_and_filter_batches(old_counts, new_counts)


def _usable_rater_rows(old_results: pd.DataFrame) -> pd.DataFrame:
    post_ids = _stripped_values(old_results[RESULTS_ID_COLUMN])
    raters = _stripped_values(old_results[RATER_COLUMN])
    usable = _is_nonempty(post_ids) & _is_nonempty(raters)
    return pd.DataFrame(
        {RESULTS_ID_COLUMN: post_ids.loc[usable], RATER_COLUMN: raters.loc[usable]}
    )


def _stripped_values(values: pd.Series) -> pd.Series:
    return values.fillna(EMPTY_CELL).astype(str).str.strip()


def _is_nonempty(values: pd.Series) -> pd.Series:
    return (values != EMPTY_CELL) & (values.str.lower() != NAN_CELL)


def _require_no_id_overlap(old_ids: pd.Series, new_ids: pd.Series) -> None:
    overlap = set(old_ids) & set(new_ids)
    if overlap:
        raise ValueError(f"overlapping id {sorted(overlap)[0]}")


def _sort_remaining_rows(remaining: pd.DataFrame) -> pd.DataFrame:
    ranked = remaining.copy()
    ranked[BATCH_RANK_COLUMN] = ranked[OUTPUT_BATCH_COLUMN].map(BATCH_SORT_RANK)
    ordered = ranked.sort_values([BATCH_RANK_COLUMN, OUTPUT_ID_COLUMN], kind=SORT_KIND)
    return ordered.drop(columns=[BATCH_RANK_COLUMN]).reset_index(drop=True)
