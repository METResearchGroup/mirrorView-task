from __future__ import annotations

import hashlib

import pytest

from data_platform.ingestion.generate_record_id import (
    INTEGRATION_BLUESKY,
    INTEGRATION_REDDIT,
    INTEGRATION_TWITTER,
    RECORD_ID_COLUMN,
    attach_record_id,
    generate_record_id,
)
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def _expected_bluesky_record_id(uri: str) -> str:
    return f"{INTEGRATION_BLUESKY}_{hashlib.sha256(uri.encode('utf-8')).hexdigest()}"


BLUESKY_URI = "at://did:plc:example/app.bsky.feed.post/abc"
REDDIT_COMMENT_FULLNAME = "t1_keep"
REDDIT_POST_ID = "abc123"
REDDIT_COMMENT_ID = "keep"
TWITTER_TWEET_ID = "1000000000000000001"


class TestGenerateRecordId:
    """Tests for generate_record_id()."""

    def test_hashes_bluesky_uri_with_integration_prefix(self) -> None:
        """Bluesky ids use sha256(uri) after the bluesky_ prefix."""
        expected = _expected_bluesky_record_id(BLUESKY_URI)

        result = generate_record_id(INTEGRATION_BLUESKY, BLUESKY_URI)

        assert result == expected

    def test_prefixes_twitter_tweet_id(self) -> None:
        """Twitter ids keep tweet_id after the twitter_ prefix."""
        expected = f"{INTEGRATION_TWITTER}_{TWITTER_TWEET_ID}"

        result = generate_record_id(INTEGRATION_TWITTER, TWITTER_TWEET_ID)

        assert result == expected

    def test_prefixes_reddit_post_and_comment_id(self) -> None:
        """Reddit comment ids join post_reddit_id and comment_id after the reddit_ prefix."""
        expected = f"{INTEGRATION_REDDIT}_{REDDIT_POST_ID}_{REDDIT_COMMENT_ID}"

        result = generate_record_id(
            INTEGRATION_REDDIT,
            f"{REDDIT_POST_ID}_{REDDIT_COMMENT_ID}",
        )

        assert result == expected

    @pytest.mark.parametrize("integration", ["mastodon", ""])
    def test_rejects_unknown_integration(self, integration: str) -> None:
        """Unknown integrations fail before id formatting."""
        with pytest.raises(ValueError, match="integration"):
            generate_record_id(integration, "id")

    @pytest.mark.parametrize("primary_key", ["", "   "])
    def test_rejects_empty_primary_key(self, primary_key: str) -> None:
        """Empty platform ids are invalid."""
        with pytest.raises(ValueError, match="non-empty"):
            generate_record_id(INTEGRATION_TWITTER, primary_key)


class TestAttachRecordId:
    """Tests for attach_record_id()."""

    def test_adds_record_id_without_mutating_input(self) -> None:
        """attach_record_id copies the row and leaves the source dict unchanged."""
        source = mock_tweet_row(TWITTER_TWEET_ID)
        source_without_record_id = {
            key: value for key, value in source.items() if key != RECORD_ID_COLUMN
        }
        expected_record_id = f"{INTEGRATION_TWITTER}_{TWITTER_TWEET_ID}"

        result = attach_record_id(source_without_record_id, INTEGRATION_TWITTER)

        assert result[RECORD_ID_COLUMN] == expected_record_id
        assert RECORD_ID_COLUMN not in source_without_record_id

    def test_raises_when_primary_key_column_is_missing(self) -> None:
        """Missing platform primary key columns are caller errors."""
        with pytest.raises(KeyError):
            attach_record_id({"text": "hello"}, INTEGRATION_TWITTER)

    def test_attaches_reddit_comment_record_id(self) -> None:
        """Reddit rows use post_reddit_id and comment_id as the primary key source."""
        source = mock_comment_row(REDDIT_COMMENT_FULLNAME, subreddit="politics")
        expected_record_id = f"{INTEGRATION_REDDIT}_{REDDIT_POST_ID}_{REDDIT_COMMENT_ID}"

        result = attach_record_id(
            source,
            INTEGRATION_REDDIT,
            records_file_stem="comments",
        )

        assert result[RECORD_ID_COLUMN] == expected_record_id
        assert result["comment_fullname"] == REDDIT_COMMENT_FULLNAME
