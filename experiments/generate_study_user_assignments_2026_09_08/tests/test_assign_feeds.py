"""Tests for assign_feeds()."""

from collections import Counter

import pandas as pd

from experiments.generate_study_user_assignments_2026_09_08.assign import (
    assign_feeds,
    count_feed_kinds,
)
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    CELL_COLUMN,
    FeedKind,
    LEFT_POSTS_IN_LEFT_ONLY,
    LEFT_POSTS_IN_TEN_TEN,
    POST_ID_COLUMN,
    POSTS_PER_FEED,
    REMAINING_COUNT_COLUMN,
    RIGHT_POSTS_IN_LEFT_ONLY,
    RIGHT_POSTS_IN_TEN_TEN,
    STANCE_COLUMN,
    STANCE_LEFT,
    STANCE_RIGHT,
)


def _stance_counts(assignment, joined: pd.DataFrame) -> tuple[int, int]:
    stance_by_id = dict(
        zip(joined[POST_ID_COLUMN].astype(str), joined[STANCE_COLUMN])
    )
    left = sum(stance_by_id[post_id] == STANCE_LEFT for post_id in assignment.post_ids)
    right = sum(stance_by_id[post_id] == STANCE_RIGHT for post_id in assignment.post_ids)
    return left, right


def _cell_counts(assignment, joined: pd.DataFrame) -> tuple[int, ...]:
    cell_by_id = dict(zip(joined[POST_ID_COLUMN].astype(str), joined[CELL_COLUMN]))
    counts = Counter(cell_by_id[post_id] for post_id in assignment.post_ids)
    return tuple(counts.get(cell, 0) for cell in range(1, 7))


def _remaining_by_stance(joined: pd.DataFrame) -> tuple[int, int]:
    left = int(
        joined.loc[joined[STANCE_COLUMN] == STANCE_LEFT, REMAINING_COUNT_COLUMN].sum()
    )
    right = int(
        joined.loc[joined[STANCE_COLUMN] == STANCE_RIGHT, REMAINING_COUNT_COLUMN].sum()
    )
    return left, right


def _assigned_slots_by_stance(assignments, joined: pd.DataFrame) -> tuple[int, int]:
    left = 0
    right = 0
    for assignment in assignments:
        feed_left, feed_right = _stance_counts(assignment, joined)
        left += feed_left
        right += feed_right
    return left, right


class TestAssignFeeds:
    """Tests for assign_feeds()."""

    def test_every_feed_is_ten_ten_or_left_only(
        self, leftover_left_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies every feed is 10:10 or 20:0, never 11:9 or 12:8."""
        result = assign_feeds(leftover_left_joined_frame)

        mixes = [_stance_counts(assignment, leftover_left_joined_frame) for assignment in result]
        allowed = {
            (LEFT_POSTS_IN_TEN_TEN, RIGHT_POSTS_IN_TEN_TEN),
            (LEFT_POSTS_IN_LEFT_ONLY, RIGHT_POSTS_IN_LEFT_ONLY),
        }
        assert set(mixes) <= allowed
        assert (11, 9) not in mixes
        assert (12, 8) not in mixes

    def test_ten_ten_feeds_come_before_left_only(
        self, leftover_left_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies all 10:10 feeds are written before left-only feeds."""
        result = assign_feeds(leftover_left_joined_frame)

        kinds = [assignment.feed_kind for assignment in result]
        first_left_only = kinds.index(FeedKind.LEFT_ONLY)
        assert FeedKind.TEN_TEN not in kinds[first_left_only:]

    def test_no_duplicate_post_in_a_feed(
        self, leftover_left_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies a post id does not repeat inside one feed."""
        result = assign_feeds(leftover_left_joined_frame)

        for assignment in result:
            assert len(assignment.post_ids) == POSTS_PER_FEED
            assert len(set(assignment.post_ids)) == POSTS_PER_FEED

    def test_covers_remaining_on_21_left_and_10_right(
        self, leftover_left_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies leftover left remaining becomes a left-only feed and unused remaining is 0."""
        original_left, original_right = _remaining_by_stance(leftover_left_joined_frame)
        expected_kinds = count_feed_kinds(original_left, original_right)

        result = assign_feeds(leftover_left_joined_frame)
        assigned_left, assigned_right = _assigned_slots_by_stance(
            result, leftover_left_joined_frame
        )

        assert len(result) == expected_kinds.user_count
        assert assigned_left >= original_left
        assert assigned_right >= original_right
        extra_left = assigned_left - original_left
        extra_right = assigned_right - original_right
        unused_left = max(0, original_left - assigned_left)
        unused_right = max(0, original_right - assigned_right)
        assert unused_left == 0
        assert unused_right == 0
        assert extra_left == 9
        assert extra_right == 0
        assert _stance_counts(result[1], leftover_left_joined_frame) == (
            LEFT_POSTS_IN_LEFT_ONLY,
            RIGHT_POSTS_IN_LEFT_ONLY,
        )

    def test_steal_stays_in_left_party(
        self, steal_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies a 10:10 feed still has 10 left when left-high remaining is 0."""
        result = assign_feeds(steal_joined_frame)
        first_ten_ten = next(
            assignment
            for assignment in result
            if assignment.feed_kind is FeedKind.TEN_TEN
        )

        left, right = _stance_counts(first_ten_ten, steal_joined_frame)
        assert left == LEFT_POSTS_IN_TEN_TEN
        assert right == RIGHT_POSTS_IN_TEN_TEN
        assert _cell_counts(first_ten_ten, steal_joined_frame)[2] == 0

    def test_left_only_never_takes_right(
        self, leftover_left_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies left-only feeds contain only left posts."""
        result = assign_feeds(leftover_left_joined_frame)

        for assignment in result:
            if assignment.feed_kind is FeedKind.LEFT_ONLY:
                left, right = _stance_counts(assignment, leftover_left_joined_frame)
                assert left == LEFT_POSTS_IN_LEFT_ONLY
                assert right == 0
                assert assignment.cell_counts[3:] == (0, 0, 0)

    def test_preferred_recipes_when_cells_have_remaining(
        self, recipe_joined_frame: pd.DataFrame
    ) -> None:
        """Verifies odd/even recipes inside each feed kind when remaining allows."""
        result = assign_feeds(recipe_joined_frame)
        ten_ten = [
            assignment
            for assignment in result
            if assignment.feed_kind is FeedKind.TEN_TEN
        ]
        left_only = [
            assignment
            for assignment in result
            if assignment.feed_kind is FeedKind.LEFT_ONLY
        ]

        assert ten_ten[0].cell_counts == (2, 5, 3, 2, 5, 3)
        assert ten_ten[1].cell_counts == (3, 5, 2, 3, 5, 2)
        assert left_only[0].cell_counts == (4, 10, 6, 0, 0, 0)
        assert left_only[1].cell_counts == (6, 10, 4, 0, 0, 0)
