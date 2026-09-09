"""Tests for split_by_party() and leftover-left counts."""

from __future__ import annotations

import json

import pytest

from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CONDITION,
    DEMOCRAT_LEFT_ONLY_COUNT,
    DEMOCRAT_ROW_COUNT,
    EMPTY_POLITICAL_PARTY,
    EXPECTED_SOURCE_ROWS,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    POSTS_PER_FEED,
    REPUBLICAN_LEFT_ONLY_COUNT,
    REPUBLICAN_ROW_COUNT,
    USER_ID_PREFIX,
    leftover_left_user_ids,
)
from experiments.load_study_assignments_2026_09_09.split import (
    count_leftover_left_users,
    parse_original_user_id,
    party_for_user_id,
    rewrite_ids,
    split_by_party,
)

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


def _source_rows(count: int = EXPECTED_SOURCE_ROWS) -> list[AssignmentRow]:
    return [_source_row(user_id) for user_id in range(1, count + 1)]


class TestParseOriginalUserId:
    """Tests for parse_original_user_id()."""

    def test_strips_user_prefix(self) -> None:
        """Verifies user-0001 parses as 1."""
        result = parse_original_user_id("user-0001")

        assert result == 1

    def test_raises_when_prefix_is_missing(self) -> None:
        """Verifies ids without the user- prefix are rejected."""
        with pytest.raises(ValueError):
            parse_original_user_id("democrat-training_assisted-0001")

    def test_raises_when_user_id_is_less_than_one(self) -> None:
        """Verifies user-0000 is rejected."""
        with pytest.raises(ValueError):
            parse_original_user_id("user-0000")


class TestPartyForUserId:
    """Tests for party_for_user_id()."""

    def test_odd_user_is_democrat(self) -> None:
        """Verifies original user 1 is Democrat."""
        result = party_for_user_id(1)

        assert result == PARTY_DEMOCRAT

    def test_even_user_is_republican(self) -> None:
        """Verifies original user 2 is Republican."""
        result = party_for_user_id(2)

        assert result == PARTY_REPUBLICAN


class TestSplitByParty:
    """Tests for split_by_party()."""

    def test_3879_rows_split_1940_and_1939(self) -> None:
        """Verifies 3,879 source rows yield 1,940 Democrat and 1,939 Republican rows."""
        result_democrat, result_republican = split_by_party(_source_rows())

        assert len(result_democrat) == DEMOCRAT_ROW_COUNT
        assert len(result_republican) == REPUBLICAN_ROW_COUNT

    def test_leftover_left_users_split_339_and_338(self) -> None:
        """Verifies leftover-left original users 3203-3879 split 339 / 338."""
        leftover_ids = leftover_left_user_ids()
        democrat, republican = split_by_party(_source_rows())

        assert count_leftover_left_users(democrat, leftover_ids) == DEMOCRAT_LEFT_ONLY_COUNT
        assert (
            count_leftover_left_users(republican, leftover_ids)
            == REPUBLICAN_LEFT_ONLY_COUNT
        )

    def test_source_row_does_not_appear_in_both_party_files(self) -> None:
        """Verifies assigned_post_ids JSON strings are not copied to both parties."""
        democrat, republican = split_by_party(_source_rows())
        democrat_json = {row.assigned_post_ids for row in democrat}
        republican_json = {row.assigned_post_ids for row in republican}

        assert democrat_json.isdisjoint(republican_json)

    def test_sorts_each_party_by_original_user_id(self) -> None:
        """Verifies Democrat rows are ordered by original user id."""
        democrat, _republican = split_by_party(_source_rows(4))

        assert [parse_original_user_id(row.id) for row in democrat] == [1, 3]


class TestRewriteIdsWithSplit:
    """Tests for rewrite_ids() after split_by_party()."""

    def test_odd_user_1_maps_to_democrat_0001(self) -> None:
        """Verifies original user 1 becomes democrat-training_assisted-0001."""
        democrat, republican = split_by_party(_source_rows(2))
        result = rewrite_ids(democrat, PARTY_DEMOCRAT)

        assert result[0].id == "democrat-training_assisted-0001"
        assert rewrite_ids(republican, PARTY_REPUBLICAN)[0].id == (
            "republican-training_assisted-0001"
        )
