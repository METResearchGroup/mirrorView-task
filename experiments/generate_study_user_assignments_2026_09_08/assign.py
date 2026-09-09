"""Assign remaining labels to 20-post study feeds.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

from dataclasses import dataclass

from experiments.generate_study_user_assignments_2026_09_08.constants import (
    CATALOG_SHUFFLE_SEED,
    CELL_COLUMN,
    CELL_COUNT,
    FeedKind,
    FeedKindCounts,
    LEFT_CELLS,
    LEFT_POSTS_IN_LEFT_ONLY,
    LEFT_POSTS_IN_TEN_TEN,
    ODD_REMAINDER,
    POST_ID_COLUMN,
    RECIPE_LEFT_ONLY_EVEN,
    RECIPE_LEFT_ONLY_ODD,
    RECIPE_TEN_TEN_EVEN,
    RECIPE_TEN_TEN_ODD,
    REMAINING_COUNT_COLUMN,
    RIGHT_CELLS,
    STANCE_COLUMN,
    STANCE_LEFT,
    STANCE_RIGHT,
    USER_ID_START,
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
    shuffled = joined.sample(frac=1, random_state=CATALOG_SHUFFLE_SEED).reset_index(
        drop=True
    )
    state = _pool_state(shuffled)
    kinds = count_feed_kinds(
        _remaining_sum(shuffled, STANCE_LEFT),
        _remaining_sum(shuffled, STANCE_RIGHT),
    )
    return _fill_kinds(state, kinds)


@dataclass
class _PoolState:
    remaining: dict[str, int]
    pools: dict[int, list[str]]
    indexes: dict[int, int]
    cell_by_id: dict[str, int]


def _remaining_sum(joined: pd.DataFrame, stance: str) -> int:
    return int(joined.loc[joined[STANCE_COLUMN] == stance, REMAINING_COUNT_COLUMN].sum())


def _pool_state(joined: pd.DataFrame) -> _PoolState:
    post_ids = joined[POST_ID_COLUMN].astype(str)
    cells = joined[CELL_COLUMN].astype(int)
    pools = {cell: [] for cell in range(1, CELL_COUNT + 1)}
    for post_id, cell in zip(post_ids, cells):
        pools[cell].append(post_id)
    return _PoolState(
        remaining=dict(zip(post_ids, joined[REMAINING_COUNT_COLUMN].astype(int))),
        pools=pools,
        indexes={cell: 0 for cell in pools},
        cell_by_id=dict(zip(post_ids, cells)),
    )


def _fill_kinds(state: _PoolState, kinds: FeedKindCounts) -> list[UserAssignment]:
    assignments = _fill_kind(state, FeedKind.TEN_TEN, kinds.ten_ten_count, USER_ID_START)
    next_user_id = USER_ID_START + kinds.ten_ten_count
    assignments.extend(
        _fill_kind(state, FeedKind.LEFT_ONLY, kinds.left_only_count, next_user_id)
    )
    return assignments


def _fill_kind(
    state: _PoolState, feed_kind: FeedKind, count: int, first_user_id: int
) -> list[UserAssignment]:
    assignments = []
    for index_within_kind in range(1, count + 1):
        user_id = first_user_id + index_within_kind - 1
        assignments.append(_fill_feed(state, feed_kind, index_within_kind, user_id))
    return assignments


def _fill_feed(
    state: _PoolState, feed_kind: FeedKind, index_within_kind: int, user_id: int
) -> UserAssignment:
    preferred = preferred_cell_counts(feed_kind, index_within_kind)
    selected: list[str] = []
    cell_counts = [0] * CELL_COUNT
    for cell, needed in enumerate(preferred, start=1):
        selected.extend(_take_for_cell(state, cell, needed, set(selected)))
    for post_id in selected:
        cell_counts[state.cell_by_id[post_id] - 1] += 1
        state.remaining[post_id] -= 1
    return UserAssignment(
        user_id=user_id,
        post_ids=tuple(shuffle_feed(selected, user_id)),
        feed_kind=feed_kind,
        cell_counts=tuple(cell_counts),
    )


def _take_for_cell(
    state: _PoolState, cell: int, needed: int, used: set[str]
) -> list[str]:
    if needed == 0:
        return []
    party = LEFT_CELLS if cell in LEFT_CELLS else RIGHT_CELLS
    taken = _take_posts(state, cell, needed, used, allow_zero=False)
    taken.extend(_steal_remaining(state, party, cell, needed - len(taken), used | set(taken)))
    taken.extend(_steal_wrap(state, party, needed - len(taken), used | set(taken)))
    if len(taken) < needed:
        raise ValueError("party cannot fill requested posts")
    return taken


def _steal_remaining(
    state: _PoolState, party: tuple[int, ...], preferred_cell: int, needed: int, used: set[str]
) -> list[str]:
    taken: list[str] = []
    for cell in party:
        if needed - len(taken) == 0 or cell == preferred_cell:
            continue
        taken.extend(
            _take_posts(state, cell, needed - len(taken), used | set(taken), False)
        )
    return taken


def _steal_wrap(
    state: _PoolState, party: tuple[int, ...], needed: int, used: set[str]
) -> list[str]:
    taken: list[str] = []
    for cell in party:
        if needed - len(taken) == 0:
            break
        taken.extend(_take_posts(state, cell, needed - len(taken), used | set(taken), True))
    return taken


def _take_posts(
    state: _PoolState, cell: int, needed: int, used: set[str], allow_zero: bool
) -> list[str]:
    posts = state.pools[cell]
    if needed == 0 or not posts:
        return []
    taken: list[str] = []
    scanned = 0
    while len(taken) < needed and scanned < len(posts):
        post_id = posts[state.indexes[cell]]
        state.indexes[cell] = (state.indexes[cell] + 1) % len(posts)
        scanned += 1
        if post_id in used or post_id in taken:
            continue
        if not allow_zero and state.remaining[post_id] <= 0:
            continue
        taken.append(post_id)
    return taken


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
