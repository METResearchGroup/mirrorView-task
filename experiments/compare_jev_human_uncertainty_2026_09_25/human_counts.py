"""Count remove votes for posts with five labelers.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
"""

from __future__ import annotations

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    REQUIRED_LABELERS,
)


def select_scored_trials(raw: pd.DataFrame) -> pd.DataFrame:
    """Keep moderation trials with a post id and a keep or remove decision.

    Parameters
    ----------
    raw
        Part 2 and Part 3 session export.

    Returns
    -------
    pandas.DataFrame
        Scored moderation trials.

    Raises
    ------
    KeyError
        When ``trial_type``, ``post_id``, ``decision``, or ``prolific_id`` is missing.
    """
    raise NotImplementedError


def dedupe_labeler_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Keep the first trial for each person and post.

    Parameters
    ----------
    trials
        Scored moderation trials.

    Returns
    -------
    pandas.DataFrame
        One row per ``prolific_id`` and ``post_id``.

    Raises
    ------
    KeyError
        When ``prolific_id``, ``post_id``, ``time_elapsed``, or ``trial_index`` is missing.
    """
    raise NotImplementedError


def aggregate_remove_counts(trials: pd.DataFrame) -> pd.DataFrame:
    """Return one row per post with rater and remove counts.

    Parameters
    ----------
    trials
        Deduped scored trials.

    Returns
    -------
    pandas.DataFrame
        Columns ``post_id``, ``n_raters``, and ``n_remove``, sorted by ``post_id``.
    """
    raise NotImplementedError


def posts_with_labeler_count(counts: pd.DataFrame, labeler_count: int) -> pd.DataFrame:
    """Keep posts whose rater count equals ``labeler_count``.

    Parameters
    ----------
    counts
        Per-post remove counts.
    labeler_count
        Required number of labelers. Must be at least 1.

    Returns
    -------
    pandas.DataFrame
        Posts with that rater count.

    Raises
    ------
    ValueError
        When ``labeler_count`` is below 1.
    """
    raise NotImplementedError


def build_five_labeler_counts(raw: pd.DataFrame) -> pd.DataFrame:
    """Return posts that have five labelers and a remove-vote count.

    Parameters
    ----------
    raw
        Part 2 and Part 3 session export.

    Returns
    -------
    pandas.DataFrame
        One row per five-labeler post, with ``n_raters`` and ``n_remove``.
    """
    trials = select_scored_trials(raw)
    deduped = dedupe_labeler_post(trials)
    counts = aggregate_remove_counts(deduped)
    return posts_with_labeler_count(counts, REQUIRED_LABELERS)
