"""Select, sample, and clone mixed 10 left and 10 right assignment rows.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

import json

import numpy as np

from experiments.generate_study_user_assignments_2026_09_08.assign import (
    shuffle_feed,
)
from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CONDITION,
    EMPTY_POLITICAL_PARTY,
    USER_ID_PREFIX,
)
from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    feed_kind,
    parse_post_ids,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    MINIMUM_CLONE_COUNT,
    SAMPLE_WITH_REPLACEMENT,
    USER_ID_DIGIT_WIDTH,
)


def select_mixed_rows(
    rows: list[AssignmentRow], stance_by_post: dict[str, str]
) -> list[AssignmentRow]:
    """Return rows whose catalog stance split is 10 left and 10 right.

    Raises
    ------
    ValueError
        When a row is neither mixed nor leftover-left.
    """
    return [
        row
        for row in rows
        if _row_kind(row, stance_by_post) is FeedKind.TEN_TEN
    ]


def _row_kind(row: AssignmentRow, stance_by_post: dict[str, str]) -> FeedKind:
    return feed_kind(parse_post_ids(row.assigned_post_ids), stance_by_post)


def sample_mixed_feeds(
    mixed_rows: list[AssignmentRow], count: int, seed: int
) -> list[AssignmentRow]:
    """Sample ``count`` mixed rows without replacement.

    Raises
    ------
    ValueError
        When ``count`` is less than 1 or greater than ``len(mixed_rows)``.
    """
    _require_sample_count(count, len(mixed_rows))
    rng = np.random.Generator(np.random.PCG64(seed))
    indexes = rng.choice(
        len(mixed_rows), size=count, replace=SAMPLE_WITH_REPLACEMENT
    )
    return [mixed_rows[index] for index in indexes]


def _require_sample_count(count: int, pool_size: int) -> None:
    if count < MINIMUM_CLONE_COUNT or count > pool_size:
        raise ValueError(f"count={count} pool={pool_size}")


def clone_mixed_feeds(
    sampled_rows: list[AssignmentRow], first_user_id: int, created_at: str
) -> list[AssignmentRow]:
    """Return copies with new user ids and reshuffled post order.

    The set of 20 post ids on each clone equals the source set.

    Raises
    ------
    ValueError
        When a source row does not parse as 20 post ids.
    """
    return [
        _clone_row(row, first_user_id + offset, created_at)
        for offset, row in enumerate(sampled_rows)
    ]


def _clone_row(
    source: AssignmentRow, user_id: int, created_at: str
) -> AssignmentRow:
    shuffled = shuffle_feed(parse_post_ids(source.assigned_post_ids), user_id)
    return AssignmentRow(
        id=_format_user_id(user_id),
        assigned_post_ids=json.dumps(shuffled),
        political_party=EMPTY_POLITICAL_PARTY,
        condition=CONDITION,
        created_at=created_at,
    )


def _format_user_id(user_id: int) -> str:
    return f"{USER_ID_PREFIX}{user_id:0{USER_ID_DIGIT_WIDTH}d}"


def concat_source_rows(
    base_rows: list[AssignmentRow], extra_rows: list[AssignmentRow]
) -> list[AssignmentRow]:
    """Return base rows followed by extra rows without mutating ``base_rows``."""
    return [*base_rows, *extra_rows]
