"""Compute remaining labels for old and new stimulus posts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import pandas as pd


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError


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
    raise NotImplementedError
