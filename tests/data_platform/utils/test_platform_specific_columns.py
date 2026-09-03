from data_platform.utils.platform_specific_columns import (
    BLUESKY_COLUMNS,
    REDDIT_COLUMNS,
    REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN,
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
    STANDARDIZED_TEXT_COLUMN,
    TWITTER_COLUMNS,
)


class TestRedditColumns:
    """Tests for REDDIT_COLUMNS text mapping."""

    def test_text_column_is_standardized_text(self) -> None:
        """Feature generation and curate read Reddit comment text from ``text``."""
        assert REDDIT_COLUMNS.text_column == STANDARDIZED_TEXT_COLUMN

    def test_original_platform_comment_text_stays_on_body(self) -> None:
        """Raw and preprocessed Reddit comments keep original ``body``."""
        assert REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN == "body"

    def test_feature_file_id_column_is_shared_source_record_id(self) -> None:
        """Feature CSVs store Reddit comment ids under shared source_record_id."""
        assert REDDIT_COLUMNS.feature_file_id_column == STANDARDIZED_SOURCE_RECORD_ID_COLUMN


class TestBlueskyColumns:
    """Tests for BLUESKY_COLUMNS feature id mapping."""

    def test_feature_file_id_column_is_shared_source_record_id(self) -> None:
        """Feature CSVs store Bluesky post ids under shared source_record_id."""
        assert BLUESKY_COLUMNS.feature_file_id_column == STANDARDIZED_SOURCE_RECORD_ID_COLUMN

    def test_records_id_column_stays_uri(self) -> None:
        """Preprocessed Bluesky rows keep original ``uri``."""
        assert BLUESKY_COLUMNS.records_id_column == "uri"


class TestTwitterColumns:
    """Tests for TWITTER_COLUMNS feature id mapping."""

    def test_feature_file_id_column_is_shared_source_record_id(self) -> None:
        """Feature CSVs store Twitter post ids under shared source_record_id."""
        assert TWITTER_COLUMNS.feature_file_id_column == STANDARDIZED_SOURCE_RECORD_ID_COLUMN

    def test_records_id_column_stays_tweet_id(self) -> None:
        """Preprocessed Twitter rows keep original ``tweet_id``."""
        assert TWITTER_COLUMNS.records_id_column == "tweet_id"
