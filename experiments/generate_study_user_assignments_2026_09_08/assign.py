"""Assign remaining labels to 20-post study feeds.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from experiments.generate_study_user_assignments_2026_09_08.constants import (
    FeedKind,
    FeedKindCounts,
    LEFT_POSTS_IN_LEFT_ONLY,
    LEFT_POSTS_IN_TEN_TEN,
    ODD_REMAINDER,
    RECIPE_LEFT_ONLY_EVEN,
    RECIPE_LEFT_ONLY_ODD,
    RECIPE_TEN_TEN_EVEN,
    RECIPE_TEN_TEN_ODD,
    UserAssignment,
)

PREFERRED_COUNTS = {
    (FeedKind.TEN_TEN, True): RECIPE_TEN_TEN_ODD,
    (FeedKind.TEN_TEN, False): RECIPE_TEN_TEN_EVEN,
    (FeedKind.LEFT_ONLY, True): RECIPE_LEFT_ONLY_ODD,
    (FeedKind.LEFT_ONLY, False): RECIPE_LEFT_ONLY_EVEN,
}


def count_feed_kinds(left_remaining: int, right_remaining: int) -> FeedKindCounts:
    """Count 10:10 feeds then left-only feeds from remaining labels.

    Parameters
    ----------
    left_remaining
        Sum of remaining labels on left posts.
    right_remaining
        Sum of remaining labels on right posts.

    Returns
    -------
    FeedKindCounts
        10:10 count, leftover left remaining, left-only count, and user count.

    Raises
    ------
    ValueError
        When leftover left remaining would be less than 0.
    """
    ten_ten_count = math.ceil(right_remaining / LEFT_POSTS_IN_TEN_TEN)
    leftover_left_remaining = left_remaining - LEFT_POSTS_IN_TEN_TEN * ten_ten_count
    if leftover_left_remaining < 0:
        raise ValueError("leftover left remaining is less than 0")
    left_only_count = _left_only_count(leftover_left_remaining)
    return FeedKindCounts(
        ten_ten_count=ten_ten_count,
        left_only_count=left_only_count,
        leftover_left_remaining=leftover_left_remaining,
        user_count=ten_ten_count + left_only_count,
    )


def _left_only_count(leftover_left_remaining: int) -> int:
    if leftover_left_remaining == 0:
        return 0
    return math.ceil(leftover_left_remaining / LEFT_POSTS_IN_LEFT_ONLY)


def preferred_cell_counts(
    feed_kind: FeedKind, index_within_kind: int
) -> tuple[int, int, int, int, int, int]:
    """Return preferred per-cell counts for a 1-based index inside a feed kind.

    Parameters
    ----------
    feed_kind
        10:10 or left-only.
    index_within_kind
        1-based index inside that feed kind. Odd indexes use recipe 1.

    Returns
    -------
    tuple[int, int, int, int, int, int]
        Preferred counts for cells 1 through 6.
    """
    is_odd = index_within_kind % 2 == ODD_REMAINDER
    return PREFERRED_COUNTS[(feed_kind, is_odd)]


def assign_feeds(joined: pd.DataFrame) -> list[UserAssignment]:
    """Fill 10:10 feeds first, then left-only feeds, stealing only inside a party.

    Parameters
    ----------
    joined
        Joined remaining-label rows with cell membership.

    Returns
    -------
    list[UserAssignment]
        One assignment per user, 10:10 feeds before left-only feeds.

    Raises
    ------
    ValueError
        When a party cannot fill its requested post count.
    """
    raise NotImplementedError


def shuffle_feed(post_ids: list[str], user_id: int) -> list[str]:
    """Shuffle 20 post ids with a numpy generator seeded by the user id.

    Parameters
    ----------
    post_ids
        Twenty post ids in recipe order.
    user_id
        1-based user id used as the generator seed.

    Returns
    -------
    list[str]
        The same ids in shuffled order.
    """
    rng = np.random.Generator(np.random.PCG64(user_id))
    order = rng.permutation(len(post_ids))
    return [post_ids[index] for index in order]
