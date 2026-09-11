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
LEFT_POST_IDS = [f"left-{index}" for index in range(10)]
RIGHT_POST_IDS = [f"right-{index}" for index in range(10)]
MIXED_POST_IDS = LEFT_POST_IDS + RIGHT_POST_IDS
LEFTOVER_LEFT_POST_IDS = [f"left-only-{index}" for index in range(20)]
ELEVEN_NINE_POST_IDS = [f"left-extra-{index}" for index in range(11)] + [
    f"right-short-{index}" for index in range(9)
]
MIXED_USER_IDS = (1, 2, 3, 4)
LEFTOVER_LEFT_USER_IDS = (5, 6)


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
    mapping = {post_id: STANCE_LEFT for post_id in LEFT_POST_IDS}
    mapping.update({post_id: STANCE_RIGHT for post_id in RIGHT_POST_IDS})
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
    mixed = [source_row(user_id, MIXED_POST_IDS) for user_id in MIXED_USER_IDS]
    leftover = [
        source_row(user_id, LEFTOVER_LEFT_POST_IDS)
        for user_id in LEFTOVER_LEFT_USER_IDS
    ]
    return mixed + leftover
