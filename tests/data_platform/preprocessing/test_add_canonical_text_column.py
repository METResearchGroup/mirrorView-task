from __future__ import annotations

import pandas as pd
import pytest

from data_platform.preprocessing.preprocess_reddit import REDDIT_SPEC
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.runner import add_canonical_text_column
from data_platform.utils.platform_specific_columns import CANONICAL_TEXT_COLUMN
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


class TestAddCanonicalTextColumn:
    """Tests for add_canonical_text_column()."""

    def test_copies_reddit_body_onto_text_and_keeps_body(self) -> None:
        """Reddit comments get shared text equal to original body."""
        body = "This is a clear English comment about policy and governance."
        source = pd.DataFrame([mock_comment_row("t1_keep", subreddit="politics")])
        source.loc[0, "body"] = body

        result = add_canonical_text_column(source, REDDIT_SPEC)

        assert result.iloc[0][CANONICAL_TEXT_COLUMN] == body
        assert result.iloc[0]["body"] == body
        assert CANONICAL_TEXT_COLUMN not in source.columns

    def test_keeps_existing_twitter_text(self) -> None:
        """Twitter rows already store text; the helper leaves that value in place."""
        text = "This is a valid English tweet for preprocessing tests without external URLs."
        source = pd.DataFrame([mock_tweet_row("1000000000000000001")])
        source.loc[0, "text"] = text

        result = add_canonical_text_column(source, TWITTER_SPEC)

        assert result.iloc[0][CANONICAL_TEXT_COLUMN] == text

    def test_raises_when_original_platform_text_column_is_missing(self) -> None:
        """Missing original platform text is a caller error, not a silent empty column."""
        source = pd.DataFrame([{"comment_fullname": "t1_missing"}])

        with pytest.raises(KeyError):
            add_canonical_text_column(source, REDDIT_SPEC)
