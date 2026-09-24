"""Shared keep/remove trial filtering and label aggregation.

Used by Part 2 and Part 3 transformed label builders.
"""

from __future__ import annotations

import pandas as pd

_KEEP_REMOVE = frozenset({"keep", "remove"})


def filter_keep_remove_trials(
    raw: pd.DataFrame,
    *,
    dedupe_worker_post: bool = False,
) -> pd.DataFrame:
    """Select linked-fate keep/remove trials with a usable ``post_id``.

    When ``dedupe_worker_post`` is True, drop conflicting worker-post pairs and
    keep the earliest row per ``(prolific_id, post_id)`` by original order.

    Raises
    ------
    KeyError
        If ``evaluation_mode``, ``post_id``, or ``decision`` is missing.
    """
    raise NotImplementedError


def aggregate_modal_labels(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate trials to one modal keep/remove label per post.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    raise NotImplementedError


def aggregate_unanimous_labels(
    trials: pd.DataFrame,
    *,
    min_raters: int = 3,
) -> pd.DataFrame:
    """Aggregate trials to unanimous posts with at least ``min_raters`` raters.

    Raises
    ------
    KeyError
        If required trial columns are missing.
    ValueError
        If a post has conflicting ``original_text`` or ``mirror_text``.
    """
    raise NotImplementedError
