"""Tests for shuffle_feed()."""

from experiments.generate_study_user_assignments_2026_09_08.assign import shuffle_feed
from experiments.generate_study_user_assignments_2026_09_08.constants import POSTS_PER_FEED


class TestShuffleFeed:
    """Tests for shuffle_feed()."""

    def test_same_user_id_is_deterministic(self) -> None:
        """Verifies the same user id yields the same permutation twice."""
        post_ids = [f"post-{index}" for index in range(POSTS_PER_FEED)]

        first = shuffle_feed(post_ids, 1)
        second = shuffle_feed(post_ids, 1)

        assert first == second
        assert sorted(first) == sorted(post_ids)

    def test_result_is_permutation_for_another_user_id(self) -> None:
        """Verifies user id 2 still returns a permutation of the input."""
        post_ids = [f"post-{index}" for index in range(POSTS_PER_FEED)]

        result = shuffle_feed(post_ids, 2)

        assert sorted(result) == sorted(post_ids)
        assert len(result) == POSTS_PER_FEED
