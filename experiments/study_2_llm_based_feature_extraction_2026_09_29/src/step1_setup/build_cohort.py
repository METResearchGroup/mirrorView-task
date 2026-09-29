"""Build the five-label cohort with modal labels and stimulus text."""

from __future__ import annotations

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.human_counts import (
    build_five_labeler_counts,
)
from experiments.study_2_llm_based_feature_extraction_2026_09_29.shared.constants import (
    COHORT_COLUMNS,
    MODAL_LABEL_KEEP,
    MODAL_LABEL_REMOVE,
    MODAL_REMOVE_MIN_VOTES,
    REQUIRED_LABELERS,
)


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
    if counts["n_raters"].ne(REQUIRED_LABELERS).any():
        raise ValueError(
            f"every post must have exactly {REQUIRED_LABELERS} labelers"
        )
    labeled = counts.copy()
    remove_mask = labeled["n_remove"].ge(MODAL_REMOVE_MIN_VOTES)
    labeled["modal_label"] = MODAL_LABEL_KEEP
    labeled.loc[remove_mask, "modal_label"] = MODAL_LABEL_REMOVE
    return labeled


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
