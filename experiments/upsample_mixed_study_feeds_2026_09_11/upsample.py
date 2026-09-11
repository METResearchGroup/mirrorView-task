"""Select, sample, and clone mixed 10 left and 10 right assignment rows.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow
from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    feed_kind,
    parse_post_ids,
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
    raise NotImplementedError


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
    raise NotImplementedError


def concat_source_rows(
    base_rows: list[AssignmentRow], extra_rows: list[AssignmentRow]
) -> list[AssignmentRow]:
    """Return base rows followed by extra rows without mutating ``base_rows``."""
    raise NotImplementedError
