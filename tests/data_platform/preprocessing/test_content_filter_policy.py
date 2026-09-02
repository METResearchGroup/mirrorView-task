from __future__ import annotations

import pytest

from data_platform.preprocessing.content_filter_policy import (
    BLUESKY_POST_MAX_LENGTH,
    BLUESKY_POST_MIN_LENGTH,
    REDDIT_COMMENT_MIN_LENGTH,
    TWITTER_POST_MAX_LENGTH,
    TWITTER_POST_MIN_LENGTH,
)
from data_platform.preprocessing.validators.bluesky_validators import (
    check_if_valid_post_length,
)
from data_platform.preprocessing.validators.reddit_validators import (
    check_if_valid_reddit_comment_min_length,
)
from data_platform.preprocessing.validators.twitter_validators import (
    check_if_valid_twitter_post_length,
)


class TestContentFilterPolicy:
    """Tests for preprocess content filter policy constants."""

    def test_bluesky_post_length_bounds(self) -> None:
        """Bluesky posts keep the current 100 to 300 character bounds."""
        assert BLUESKY_POST_MIN_LENGTH == 100
        assert BLUESKY_POST_MAX_LENGTH == 300

    def test_twitter_post_length_bounds(self) -> None:
        """Twitter posts keep the current 50 to 280 character bounds."""
        assert TWITTER_POST_MIN_LENGTH == 50
        assert TWITTER_POST_MAX_LENGTH == 280

    def test_reddit_comment_minimum_length(self) -> None:
        """Reddit comments have a preprocess minimum of 30 characters and no max constant."""
        assert REDDIT_COMMENT_MIN_LENGTH == 30


class TestCheckIfValidPostLength:
    """Tests for check_if_valid_post_length()."""

    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (BLUESKY_POST_MIN_LENGTH - 1, False),
            (BLUESKY_POST_MIN_LENGTH, True),
            (BLUESKY_POST_MAX_LENGTH, True),
            (BLUESKY_POST_MAX_LENGTH + 1, False),
        ],
    )
    def test_accepts_text_within_bluesky_bounds(self, length: int, expected: bool) -> None:
        """Rejects Bluesky posts shorter than 100 or longer than 300 characters."""
        result = check_if_valid_post_length("x" * length)
        assert result is expected


class TestCheckIfValidTwitterPostLength:
    """Tests for check_if_valid_twitter_post_length()."""

    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (TWITTER_POST_MIN_LENGTH - 1, False),
            (TWITTER_POST_MIN_LENGTH, True),
            (TWITTER_POST_MAX_LENGTH, True),
            (TWITTER_POST_MAX_LENGTH + 1, False),
        ],
    )
    def test_accepts_text_within_twitter_bounds(self, length: int, expected: bool) -> None:
        """Rejects Twitter posts shorter than 50 or longer than 280 characters."""
        result = check_if_valid_twitter_post_length("x" * length)
        assert result is expected


class TestCheckIfValidRedditCommentMinLength:
    """Tests for check_if_valid_reddit_comment_min_length()."""

    @pytest.mark.parametrize(
        ("length", "expected"),
        [
            (REDDIT_COMMENT_MIN_LENGTH - 1, False),
            (REDDIT_COMMENT_MIN_LENGTH, True),
        ],
    )
    def test_accepts_text_at_or_above_reddit_minimum(
        self, length: int, expected: bool
    ) -> None:
        """Rejects Reddit comments shorter than 30 characters, and keeps 30 character text."""
        result = check_if_valid_reddit_comment_min_length("x" * length)
        assert result is expected
