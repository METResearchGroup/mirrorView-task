from __future__ import annotations

import pandas as pd
import pytest

from data_platform.preprocessing.preprocess_bluesky import BLUESKY_SPEC
from data_platform.preprocessing.preprocess_reddit import REDDIT_SPEC
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.shared_columns import add_canonical_source_record_id
from data_platform.utils.platform_specific_columns import CANONICAL_SOURCE_RECORD_ID_COLUMN
from tests.data_platform.conftest import make_post_row
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


class TestAddCanonicalSourceRecordId:
    """Tests for add_canonical_source_record_id()."""

    def test_copies_reddit_comment_fullname_and_keeps_original(self) -> None:
        """Reddit comments get shared source_record_id equal to comment_fullname."""
        comment_fullname = "t1_keep"
        source = pd.DataFrame([mock_comment_row(comment_fullname, subreddit="politics")])

        result = add_canonical_source_record_id(source, REDDIT_SPEC)

        assert result.iloc[0][CANONICAL_SOURCE_RECORD_ID_COLUMN] == comment_fullname
        assert result.iloc[0]["comment_fullname"] == comment_fullname
        assert CANONICAL_SOURCE_RECORD_ID_COLUMN not in source.columns

    def test_copies_twitter_tweet_id_and_keeps_original(self) -> None:
        """Twitter rows copy tweet_id onto source_record_id and keep tweet_id."""
        tweet_id = "1000000000000000001"
        source = pd.DataFrame([mock_tweet_row(tweet_id)])

        result = add_canonical_source_record_id(source, TWITTER_SPEC)

        assert result.iloc[0][CANONICAL_SOURCE_RECORD_ID_COLUMN] == tweet_id
        assert result.iloc[0]["tweet_id"] == tweet_id

    def test_copies_bluesky_uri_and_keeps_original(self) -> None:
        """Bluesky rows copy uri onto source_record_id and keep uri."""
        uri = "at://did:plc:example/app.bsky.feed.post/abc"
        source = pd.DataFrame([make_post_row(uri=uri)])

        result = add_canonical_source_record_id(source, BLUESKY_SPEC)

        assert result.iloc[0][CANONICAL_SOURCE_RECORD_ID_COLUMN] == uri
        assert result.iloc[0]["uri"] == uri

    def test_raises_when_reddit_comment_fullname_is_missing(self) -> None:
        """Missing original platform record id is a caller error."""
        source = pd.DataFrame([{"author": "regular_user"}])

        with pytest.raises(KeyError):
            add_canonical_source_record_id(source, REDDIT_SPEC)
