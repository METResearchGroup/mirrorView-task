from __future__ import annotations

import pandas as pd
import pytest

from data_platform.preprocessing.preprocess_bluesky import BLUESKY_SPEC
from data_platform.preprocessing.preprocess_reddit import REDDIT_SPEC
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.runner import add_canonical_author_columns
from data_platform.utils.platform_specific_columns import CANONICAL_AUTHOR_HANDLE_COLUMN
from tests.data_platform.conftest import make_post_row
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


class TestAddCanonicalAuthorColumns:
    """Tests for add_canonical_author_columns()."""

    def test_copies_reddit_author_onto_author_handle_and_keeps_author(self) -> None:
        """Reddit comments get shared author_handle equal to original author."""
        author = "regular_user"
        source = pd.DataFrame([mock_comment_row("t1_keep", subreddit="politics")])
        source.loc[0, "author"] = author

        result = add_canonical_author_columns(source, REDDIT_SPEC)

        assert result.iloc[0][CANONICAL_AUTHOR_HANDLE_COLUMN] == author
        assert result.iloc[0]["author"] == author
        assert "author_id" not in result.columns
        assert CANONICAL_AUTHOR_HANDLE_COLUMN not in source.columns

    def test_copies_twitter_username_onto_author_handle_and_keeps_native_fields(
        self,
    ) -> None:
        """Twitter rows copy username onto author_handle and keep username and author_id."""
        username = "handle"
        author_id = "123"
        source = pd.DataFrame(
            [mock_tweet_row("1000000000000000001", username=username, author_id=author_id)]
        )

        result = add_canonical_author_columns(source, TWITTER_SPEC)

        assert result.iloc[0][CANONICAL_AUTHOR_HANDLE_COLUMN] == username
        assert result.iloc[0]["username"] == username
        assert result.iloc[0]["author_id"] == author_id

    def test_keeps_existing_bluesky_author_handle(self) -> None:
        """Bluesky rows already store author_handle; the helper leaves that value in place."""
        handle = "a.bsky.social"
        source = pd.DataFrame([make_post_row(author_handle=handle)])

        result = add_canonical_author_columns(source, BLUESKY_SPEC)

        assert result.iloc[0][CANONICAL_AUTHOR_HANDLE_COLUMN] == handle
        assert "author_id" not in result.columns

    def test_raises_when_reddit_author_column_is_missing(self) -> None:
        """Missing original platform author is a caller error, not a silent empty column."""
        source = pd.DataFrame([{"comment_fullname": "t1_missing"}])

        with pytest.raises(KeyError):
            add_canonical_author_columns(source, REDDIT_SPEC)

    def test_raises_when_bluesky_author_handle_is_missing(self) -> None:
        """Missing shared author_handle on Bluesky is a caller error."""
        source = pd.DataFrame([{"uri": "at://did:plc:test/app.bsky.feed.post/1"}])

        with pytest.raises(KeyError):
            add_canonical_author_columns(source, BLUESKY_SPEC)
