"""Partition pull request 278 rows by party and rewrite assignment ids.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

import json
from dataclasses import replace

from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CONDITION,
    FeedKind,
    FIRST_ASSIGNMENT_INDEX,
    LEFT_POSTS_IN_LEFT_ONLY,
    LEFT_POSTS_IN_TEN_TEN,
    ODD_REMAINDER,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    POSTS_PER_FEED,
    RIGHT_POSTS_IN_LEFT_ONLY,
    RIGHT_POSTS_IN_TEN_TEN,
    STANCE_LEFT,
    STANCE_RIGHT,
    USER_ID_PREFIX,
    format_assignment_id,
)


def parse_original_user_id(assignment_id: str) -> int:
    """Return the integer after the ``user-`` prefix.

    Raises
    ------
    ValueError
        When the prefix is missing or the integer is less than 1.
    """
    if not assignment_id.startswith(USER_ID_PREFIX):
        raise ValueError(f"missing prefix {USER_ID_PREFIX}")
    user_id = int(assignment_id.removeprefix(USER_ID_PREFIX))
    if user_id < FIRST_ASSIGNMENT_INDEX:
        raise ValueError(f"user id {user_id} is less than 1")
    return user_id


def party_for_user_id(user_id: int) -> str:
    """Return ``democrat`` for odd ids and ``republican`` for even ids."""
    if user_id % 2 == ODD_REMAINDER:
        return PARTY_DEMOCRAT
    return PARTY_REPUBLICAN


def split_by_party(
    rows: list[AssignmentRow],
) -> tuple[list[AssignmentRow], list[AssignmentRow]]:
    """Partition rows so each feed appears in one party list.

    Each list is sorted by original user id.
    """
    democrat: list[AssignmentRow] = []
    republican: list[AssignmentRow] = []
    for row in rows:
        _append_to_party(row, democrat, republican)
    return _sorted_by_user(democrat), _sorted_by_user(republican)


def rewrite_ids(rows: list[AssignmentRow], party: str) -> list[AssignmentRow]:
    """Return copies with party ids ``{party}-training_assisted-{index:04d}``."""
    return [
        replace(
            row,
            id=format_assignment_id(party, index),
            political_party=party,
        )
        for index, row in enumerate(rows, start=FIRST_ASSIGNMENT_INDEX)
    ]


def parse_post_ids(assigned_post_ids: str) -> list[str]:
    """Parse a JSON list of 20 post ids.

    Raises
    ------
    ValueError
        When the value is not a list of 20 strings.
    """
    parsed = json.loads(assigned_post_ids)
    if not isinstance(parsed, list) or len(parsed) != POSTS_PER_FEED:
        raise ValueError("assigned_post_ids must be a JSON list of 20 ids")
    return [str(post_id) for post_id in parsed]


def feed_kind(post_ids: list[str], stance_by_post: dict[str, str]) -> FeedKind:
    """Return the 10:10 or leftover-left kind for one feed.

    Raises
    ------
    ValueError
        When the feed is neither 10 left and 10 right nor 20 left and 0 right.
    """
    left, right = count_stances(post_ids, stance_by_post)
    if left == LEFT_POSTS_IN_TEN_TEN and right == RIGHT_POSTS_IN_TEN_TEN:
        return FeedKind.TEN_TEN
    if left == LEFT_POSTS_IN_LEFT_ONLY and right == RIGHT_POSTS_IN_LEFT_ONLY:
        return FeedKind.LEFT_ONLY
    raise ValueError(f"feed mix {left}:{right}")


def count_stances(
    post_ids: list[str], stance_by_post: dict[str, str]
) -> tuple[int, int]:
    """Return left and right counts for assigned post ids.

    Raises
    ------
    ValueError
        When a post id is missing or its stance is not left or right.
    """
    stances = [_stance_for_post(post_id, stance_by_post) for post_id in post_ids]
    left = sum(stance == STANCE_LEFT for stance in stances)
    right = sum(stance == STANCE_RIGHT for stance in stances)
    return left, right


def count_kind(
    rows: list[AssignmentRow],
    stance_by_post: dict[str, str],
    kind: FeedKind,
) -> int:
    """Return how many rewritten rows have the given feed kind."""
    return sum(
        feed_kind(parse_post_ids(row.assigned_post_ids), stance_by_post) is kind
        for row in rows
    )


def count_leftover_left_users(
    rows: list[AssignmentRow], leftover_user_ids: set[int]
) -> int:
    """Return how many source rows have original user ids in the leftover set."""
    return sum(
        parse_original_user_id(row.id) in leftover_user_ids for row in rows
    )


def _append_to_party(
    row: AssignmentRow,
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
) -> None:
    if party_for_user_id(parse_original_user_id(row.id)) == PARTY_DEMOCRAT:
        democrat.append(row)
        return
    republican.append(row)


def _sorted_by_user(rows: list[AssignmentRow]) -> list[AssignmentRow]:
    return sorted(rows, key=lambda row: parse_original_user_id(row.id))


def _stance_for_post(post_id: str, stance_by_post: dict[str, str]) -> str:
    if post_id not in stance_by_post:
        raise ValueError(f"missing catalog id {post_id}")
    stance = stance_by_post[post_id]
    if stance not in {STANCE_LEFT, STANCE_RIGHT}:
        raise ValueError(f"stance {stance} is not left or right")
    return stance


def require_training_assisted(rows: list[AssignmentRow]) -> None:
    """Raise when a source row is not the training_assisted condition."""
    for row in rows:
        if row.condition != CONDITION:
            raise ValueError(f"condition {row.condition} is not {CONDITION}")
