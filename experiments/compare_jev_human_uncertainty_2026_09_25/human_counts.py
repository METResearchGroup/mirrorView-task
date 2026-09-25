"""Count remove votes for posts with five labelers.

Run from the repo root::

    PYTHONPATH=. uv run pytest experiments/compare_jev_human_uncertainty_2026_09_25/tests/test_human_counts.py -q
"""

from __future__ import annotations

import pandas as pd

from experiments.compare_jev_human_uncertainty_2026_09_25.constants import (
    DECISION_KEEP,
    DECISION_REMOVE,
    REQUIRED_LABELERS,
    TRIAL_TYPE_MODERATION,
)

_SCORED_TRIAL_COLUMNS = ("trial_type", "post_id", "decision", "prolific_id")
_DEDUPE_COLUMNS = ("prolific_id", "post_id", "time_elapsed", "trial_index")
_MINIMUM_LABELER_COUNT = 1
_BLANK_POST_ID = "nan"


def _require_columns(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    """Raise KeyError when any named column is absent."""
    missing = [name for name in columns if name not in frame.columns]
    if missing:
        raise KeyError(f"missing columns: {sorted(missing)}")


def _normalized_text(series: pd.Series) -> pd.Series:
    """Return lowercase stripped text, with missing cells as empty strings."""
    return series.fillna("").astype(str).str.lower().str.strip()


def _usable_post_id(series: pd.Series) -> pd.Series:
    """Return True for post ids that are present and not blank."""
    present = series.notna()
    text = series.fillna("").astype(str).str.strip()
    return present & text.ne("") & text.str.lower().ne(_BLANK_POST_ID)


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
    _require_columns(raw, _SCORED_TRIAL_COLUMNS)
    trial_type = _normalized_text(raw["trial_type"])
    decision = _normalized_text(raw["decision"])
    post_id_text = raw["post_id"].fillna("").astype(str).str.strip()
    keep = (
        trial_type.eq(TRIAL_TYPE_MODERATION)
        & _usable_post_id(raw["post_id"])
        & decision.isin({DECISION_KEEP, DECISION_REMOVE})
    )
    selected = raw.loc[keep].copy()
    selected["decision"] = decision.loc[selected.index]
    selected["post_id"] = post_id_text.loc[selected.index]
    return selected


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
