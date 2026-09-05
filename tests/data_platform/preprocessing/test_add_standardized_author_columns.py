from __future__ import annotations

import pandas as pd
import pytest

from data_platform.preprocessing.preprocess_bluesky import BLUESKY_SPEC
from data_platform.preprocessing.preprocess_reddit import REDDIT_SPEC
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.shared_columns import add_standardized_author_columns
from data_platform.utils.platform_specific_columns import STANDARDIZED_AUTHOR_HANDLE_COLUMN
from tests.data_platform.conftest import make_post_row
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


class TestAddStandardizedAuthorColumns:
    """Tests for add_standardized_author_columns()."""

    def test_copies_reddit_author_onto_author_handle_and_keeps_author(self) -> None:
        """Reddit comments get shared author_handle equal to original author."""
        author = "regular_user"
        source = pd.DataFrame([mock_comment_row("t1_keep")])
        source.loc[0, "author"] = author

        result = add_standardized_author_columns(source, REDDIT_SPEC)

        assert result.iloc[0][STANDARDIZED_AUTHOR_HANDLE_COLUMN] == author
        assert result.iloc[0]["author"] == author
        assert "author_id" not in result.columns
        assert STANDARDIZED_AUTHOR_HANDLE_COLUMN not in source.columns

    def test_copies_twitter_author_id_onto_author_handle_and_keeps_native_fields(
        self,
    ) -> None:
        """Verify that Twitter rows copy author_id to author_handle and preserve native columns."""
        username = ""
        author_id = "123"
        source = pd.DataFrame(
            [mock_tweet_row("1000000000000000001", username=username, author_id=author_id)]
        )

        result = add_standardized_author_columns(source, TWITTER_SPEC)

        assert result.iloc[0][STANDARDIZED_AUTHOR_HANDLE_COLUMN] == author_id
        assert result.iloc[0]["username"] == username
        assert result.iloc[0]["author_id"] == author_id

    def test_copies_bluesky_author_handle_from_source_column(self) -> None:
        """Bluesky rows copy author_handle from the named source column."""
        handle = "a.bsky.social"
        source = pd.DataFrame([make_post_row(author_handle=handle)])

        result = add_standardized_author_columns(source, BLUESKY_SPEC)

        assert result.iloc[0][STANDARDIZED_AUTHOR_HANDLE_COLUMN] == handle
        assert result.iloc[0]["author_handle"] == handle
        assert "author_id" not in result.columns

    def test_overwrites_existing_author_handle_from_source_column(self) -> None:
        """An existing author_handle value is replaced by the source column."""
        source = pd.DataFrame([mock_comment_row("t1_overwrite")])
        source.loc[0, "author"] = "from_author"
        source[STANDARDIZED_AUTHOR_HANDLE_COLUMN] = "stale_handle"

        result = add_standardized_author_columns(source, REDDIT_SPEC)

        assert result.iloc[0][STANDARDIZED_AUTHOR_HANDLE_COLUMN] == "from_author"
        assert result.iloc[0]["author"] == "from_author"

    def test_raises_when_reddit_author_column_is_missing(self) -> None:
        """Missing original platform author is a caller error, not a silent empty column."""
        source = pd.DataFrame([{"comment_fullname": "t1_missing"}])

        with pytest.raises(KeyError):
            add_standardized_author_columns(source, REDDIT_SPEC)

    def test_raises_when_bluesky_author_handle_is_missing(self) -> None:
        """Missing Bluesky author_handle source column is a caller error."""
        source = pd.DataFrame([{"uri": "at://did:plc:test/app.bsky.feed.post/1"}])

        with pytest.raises(KeyError):
            add_standardized_author_columns(source, BLUESKY_SPEC)
