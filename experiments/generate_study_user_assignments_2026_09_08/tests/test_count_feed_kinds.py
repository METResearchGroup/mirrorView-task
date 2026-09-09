"""Tests for count_feed_kinds()."""

import math

import pytest

from experiments.generate_study_user_assignments_2026_09_08.assign import count_feed_kinds
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    FeedKindCounts,
    PINNED_LEFT_REMAINING,
    PINNED_RIGHT_REMAINING,
)


class TestCountFeedKinds:
    """Tests for count_feed_kinds()."""

    def test_pr279_totals_yield_3202_then_677(self) -> None:
        """Verifies pull request 279 remaining totals maximize 10:10 then left-only."""
        expected = FeedKindCounts(
            ten_ten_count=3202,
            left_only_count=677,
            leftover_left_remaining=13522,
            user_count=3879,
        )

        result = count_feed_kinds(PINNED_LEFT_REMAINING, PINNED_RIGHT_REMAINING)

        assert result == expected

    def test_does_not_cap_left_only_at_676(self) -> None:
        """Verifies 3,878 users would leave leftover left remaining unused."""
        leftover_if_676 = PINNED_LEFT_REMAINING - 10 * 3202 - 20 * 676
        expected_unused = 2

        result = count_feed_kinds(PINNED_LEFT_REMAINING, PINNED_RIGHT_REMAINING)

        assert leftover_if_676 == expected_unused
        assert result.left_only_count != 676
        assert result.left_only_count == 677

    def test_small_imbalance_yields_one_of_each_feed_kind(self) -> None:
        """Verifies 21 left and 10 right remaining produce one 10:10 and one left-only."""
        expected = FeedKindCounts(
            ten_ten_count=1,
            left_only_count=1,
            leftover_left_remaining=11,
            user_count=2,
        )

        result = count_feed_kinds(21, 10)

        assert result == expected

    def test_raises_when_leftover_left_remaining_is_negative(self) -> None:
        """Verifies leftover left remaining less than 0 is rejected."""
        with pytest.raises(ValueError):
            count_feed_kinds(5, 20)

    def test_ten_ten_count_is_ceiling_of_right_divided_by_ten(self) -> None:
        """Verifies 10:10 count uses ceiling division of right remaining by 10."""
        right_remaining = 11
        expected_ten_ten = math.ceil(right_remaining / 10)

        result = count_feed_kinds(30, right_remaining)

        assert result.ten_ten_count == expected_ten_ten
