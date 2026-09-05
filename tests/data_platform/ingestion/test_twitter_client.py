"""Unit tests for twitter_client module functions.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/ingestion/test_twitter_client.py
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

from data_platform.ingestion.generate_record_id import attach_record_id
from data_platform.ingestion.twitter_client import (
    _append_tweets_from_response,
    _search_recent_tweets_kwargs,
    build_query,
    fetch_posts_for_keyword,
    tweet_to_row,
)
from data_platform.models.sync import SyncTwitterPostModel


def _make_mock_tweet(
    tweet_id: str = "1000000000000000001",
    text: str = "Test tweet text",
    author_id: str = "12345",
) -> SimpleNamespace:
    return SimpleNamespace(
        id=tweet_id,
        text=text,
        author_id=author_id,
        created_at=None,
        public_metrics={
            "like_count": 5,
            "retweet_count": 2,
            "reply_count": 1,
            "quote_count": 0,
        },
    )


class TestSearchRecentTweetsKwargs:
    """Tests for _search_recent_tweets_kwargs()."""

    def test_omits_expansions_and_user_fields(self) -> None:
        """Verifies expansions and user_fields are omitted to cut per-tweet cost."""
        # Arrange
        query = "mirrorview lang:en"
        max_results = 25
        next_token = None

        # Act
        result = _search_recent_tweets_kwargs(query, max_results, next_token)

        # Assert
        assert result["query"] == query
        assert result["max_results"] == max_results
        assert result["tweet_fields"] == ["created_at", "public_metrics", "author_id"]
        assert "expansions" not in result
        assert "user_fields" not in result
        assert "next_token" not in result

    def test_includes_next_token_when_present(self) -> None:
        """Verifies next_token is passed when not None."""
        # Arrange
        query = "mirrorview lang:en"
        max_results = 50
        next_token = "b26v89c19zq"

        # Act
        result = _search_recent_tweets_kwargs(query, max_results, next_token)

        # Assert
        assert result["next_token"] == next_token
        assert "expansions" not in result
        assert "user_fields" not in result


class TestTweetToRow:
    """Tests for tweet_to_row()."""

    def test_populates_empty_username_and_validates_model(self) -> None:
        """Verifies username is an empty string and row satisfies SyncTwitterPostModel."""
        # Arrange
        tweet = _make_mock_tweet(tweet_id="101", author_id="author_999")
        keyword = "ai"
        sync_timestamp = "2026_09_05-12:00:00"

        # Act
        result = tweet_to_row(
            tweet,
            keyword=keyword,
            sync_timestamp=sync_timestamp,
        )

        # Assert
        assert result["tweet_id"] == "101"
        assert result["author_id"] == "author_999"
        assert result["username"] == ""
        assert result["keyword"] == keyword
        assert result["sync_timestamp"] == sync_timestamp
        assert result["like_count"] == 5

        validated = SyncTwitterPostModel.model_validate(attach_record_id(result, "twitter"))
        assert validated.username == ""
        assert validated.author_id == "author_999"


class TestAppendTweetsFromResponse:
    """Tests for _append_tweets_from_response()."""

    def test_appends_rows_with_empty_username_and_returns_next_token(self) -> None:
        """Verifies rows are appended without user expansions and next_token is returned."""
        # Arrange
        tweet1 = _make_mock_tweet(tweet_id="1", author_id="auth_1")
        tweet2 = _make_mock_tweet(tweet_id="2", author_id="auth_2")
        response = SimpleNamespace(
            data=[tweet1, tweet2],
            meta={"next_token": "token_page_2"},
        )
        rows: list[dict[str, object]] = []

        # Act
        result = _append_tweets_from_response(
            response,
            rows,
            limit=10,
            keyword="technology",
            sync_timestamp="2026_09_05-12:00:00",
        )

        # Assert
        assert result == "token_page_2"
        assert len(rows) == 2
        assert rows[0]["author_id"] == "auth_1"
        assert rows[0]["username"] == ""
        assert rows[1]["author_id"] == "auth_2"
        assert rows[1]["username"] == ""

    def test_returns_none_when_response_is_empty(self) -> None:
        """Verifies None is returned when response has no data."""
        # Arrange
        response = SimpleNamespace(data=None)
        rows: list[dict[str, object]] = []

        # Act
        result = _append_tweets_from_response(
            response,
            rows,
            limit=10,
            keyword="technology",
            sync_timestamp="2026_09_05-12:00:00",
        )

        # Assert
        assert result is None
        assert len(rows) == 0


class TestFetchPostsForKeyword:
    """Tests for fetch_posts_for_keyword()."""

    def test_fetches_posts_without_user_expansion_kwargs(self) -> None:
        """Verifies search_recent_tweets is called with no expansions or user_fields."""
        # Arrange
        tweet = _make_mock_tweet(tweet_id="100", author_id="auth_100")
        response = SimpleNamespace(
            data=[tweet],
            meta={"next_token": None},
        )
        mock_client = MagicMock()
        mock_client.search_recent_tweets.return_value = response

        # Act
        rows, stats = fetch_posts_for_keyword(
            mock_client,
            "test_keyword",
            limit=1,
            lang="en",
            exclude=[],
            sync_timestamp="2026_09_05-12:00:00",
        )

        # Assert
        assert len(rows) == 1
        assert rows[0]["username"] == ""
        assert rows[0]["author_id"] == "auth_100"
        assert stats["rows_collected"] == 1

        mock_client.search_recent_tweets.assert_called_once()
        called_kwargs = mock_client.search_recent_tweets.call_args.kwargs
        assert "expansions" not in called_kwargs
        assert "user_fields" not in called_kwargs
        assert called_kwargs["tweet_fields"] == ["created_at", "public_metrics", "author_id"]
