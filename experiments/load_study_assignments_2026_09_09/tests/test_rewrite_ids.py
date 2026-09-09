"""Tests for rewrite_ids()."""

from __future__ import annotations

import json

from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CONDITION,
    DEMOCRAT_ROW_COUNT,
    EMPTY_POLITICAL_PARTY,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    POSTS_PER_FEED,
    USER_ID_PREFIX,
    format_assignment_id,
)
from experiments.load_study_assignments_2026_09_09.split import rewrite_ids, split_by_party

CREATED_AT = "2026_09_04-14:27:30"


def _source_row(user_id: int) -> AssignmentRow:
    post_ids = [f"post-{user_id}-{index}" for index in range(POSTS_PER_FEED)]
    return AssignmentRow(
        id=f"{USER_ID_PREFIX}{user_id:04d}",
        assigned_post_ids=json.dumps(post_ids),
        political_party=EMPTY_POLITICAL_PARTY,
        condition=CONDITION,
        created_at=CREATED_AT,
    )


class TestRewriteIds:
    """Tests for rewrite_ids()."""

    def test_odd_user_1_maps_to_democrat_training_assisted_0001(self) -> None:
        """Verifies original user 1 maps to democrat-training_assisted-0001."""
        democrat, republican = split_by_party([_source_row(1), _source_row(2)])
        result = rewrite_ids(democrat, PARTY_DEMOCRAT)
        expected = "democrat-training_assisted-0001"

        assert result[0].id == expected
        assert rewrite_ids(republican, PARTY_REPUBLICAN)[0].id == (
            "republican-training_assisted-0001"
        )

    def test_sets_political_party_and_keeps_post_ids(self) -> None:
        """Verifies party is set and assigned_post_ids, condition, and created_at stay."""
        source = _source_row(1)
        result = rewrite_ids([source], PARTY_DEMOCRAT)[0]

        assert result.political_party == PARTY_DEMOCRAT
        assert result.assigned_post_ids == source.assigned_post_ids
        assert result.condition == CONDITION
        assert result.created_at == CREATED_AT

    def test_democrat_ids_are_contiguous_through_1940(self) -> None:
        """Verifies Democrat ids are democrat-training_assisted-0001 through 1940."""
        democrat_source = [_source_row(user_id) for user_id in range(1, 3880, 2)]
        result = rewrite_ids(democrat_source, PARTY_DEMOCRAT)
        expected = [
            format_assignment_id(PARTY_DEMOCRAT, index)
            for index in range(1, DEMOCRAT_ROW_COUNT + 1)
        ]

        assert [row.id for row in result] == expected
        assert len(result) == DEMOCRAT_ROW_COUNT
