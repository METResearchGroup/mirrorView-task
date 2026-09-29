"""Build the five-label cohort with modal labels and stimulus text."""

from __future__ import annotations

import pandas as pd


def assign_modal_label(counts: pd.DataFrame) -> pd.DataFrame:
    """Add ``modal_label`` from remove-vote counts.

    Parameters
    ----------
    counts
        Per-post rater and remove counts.

    Returns
    -------
    pandas.DataFrame
        Input frame with ``modal_label`` added.

    Raises
    ------
    ValueError
        When any row does not have exactly ``REQUIRED_LABELERS`` raters.
    """
    raise NotImplementedError


def attach_pair_text(labeled: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    """Join cohort posts to stimulus text and metadata.

    Parameters
    ----------
    labeled
        Posts with modal labels and remove counts.
    stimuli
        Study 2 stimulus table.

    Returns
    -------
    pandas.DataFrame
        Cohort rows with text columns, sorted by ``post_id``.

    Raises
    ------
    ValueError
        When a labeled ``post_id`` has no matching stimulus row.
    """
    raise NotImplementedError


def build_cohort(results: pd.DataFrame, stimuli: pd.DataFrame) -> pd.DataFrame:
    """Build the five-label cohort with text and modal labels.

    Parameters
    ----------
    results
        Study 2 session export.
    stimuli
        Study 2 stimulus table.

    Returns
    -------
    pandas.DataFrame
        Cohort with ``COHORT_COLUMNS``.
    """
    raise NotImplementedError
