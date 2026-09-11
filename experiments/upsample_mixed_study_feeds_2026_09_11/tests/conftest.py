"""Shared assignment-row factories for mixed-feed upsample tests."""

from __future__ import annotations

import json

import pytest

from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CONDITION,
    EMPTY_POLITICAL_PARTY,
    STANCE_LEFT,
    STANCE_RIGHT,
    USER_ID_PREFIX,
    USER_ID_WIDTH,
)

CREATED_AT = "2026_09_04-14:27:30"
LEFTOVER_LEFT_POST_IDS = [f"left-only-{index}" for index in range(20)]
ELEVEN_NINE_POST_IDS = [f"left-extra-{index}" for index in range(11)] + [
    f"right-short-{index}" for index in range(9)
]
MIXED_USER_IDS = (1, 2, 3, 4)
LEFTOVER_LEFT_USER_IDS = (5, 6)
LEFT_POSTS_PER_MIXED = 10
RIGHT_POSTS_PER_MIXED = 10


def mixed_post_ids(user_id: int) -> list[str]:
    """Return 10 left and 10 right post ids unique to ``user_id``."""
    left = [f"left-{user_id}-{index}" for index in range(LEFT_POSTS_PER_MIXED)]
    right = [f"right-{user_id}-{index}" for index in range(RIGHT_POSTS_PER_MIXED)]
    return left + right


def source_row(
    user_id: int, post_ids: list[str], created_at: str = CREATED_AT
) -> AssignmentRow:
    """Build one source assignment row with empty party."""
    return AssignmentRow(
        id=f"{USER_ID_PREFIX}{user_id:0{USER_ID_WIDTH}d}",
        assigned_post_ids=json.dumps(post_ids),
        political_party=EMPTY_POLITICAL_PARTY,
        condition=CONDITION,
        created_at=created_at,
    )


@pytest.fixture
def stance_by_post() -> dict[str, str]:
    """Map fixture post ids to left or right stance."""
    mapping = {
        post_id: STANCE_LEFT
        for user_id in MIXED_USER_IDS
        for post_id in mixed_post_ids(user_id)[:LEFT_POSTS_PER_MIXED]
    }
    mapping.update(
        {
            post_id: STANCE_RIGHT
            for user_id in MIXED_USER_IDS
            for post_id in mixed_post_ids(user_id)[LEFT_POSTS_PER_MIXED:]
        }
    )
    mapping.update({post_id: STANCE_LEFT for post_id in LEFTOVER_LEFT_POST_IDS})
    mapping.update(
        {post_id: STANCE_LEFT for post_id in ELEVEN_NINE_POST_IDS[:11]}
    )
    mapping.update(
        {post_id: STANCE_RIGHT for post_id in ELEVEN_NINE_POST_IDS[11:]}
    )
    return mapping


@pytest.fixture
def mixed_and_leftover_rows() -> list[AssignmentRow]:
    """Four mixed feeds (users 1-4) and two leftover-left feeds (users 5-6)."""
    mixed = [source_row(user_id, mixed_post_ids(user_id)) for user_id in MIXED_USER_IDS]
    leftover = [
        source_row(user_id, LEFTOVER_LEFT_POST_IDS)
        for user_id in LEFTOVER_LEFT_USER_IDS
    ]
    return mixed + leftover
