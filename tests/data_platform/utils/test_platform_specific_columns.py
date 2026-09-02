from data_platform.utils.platform_specific_columns import (
    CANONICAL_TEXT_COLUMN,
    REDDIT_COLUMNS,
    REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN,
)


class TestRedditColumns:
    """Tests for REDDIT_COLUMNS text mapping."""

    def test_text_column_is_canonical_text(self) -> None:
        """Feature generation and curate read Reddit comment text from ``text``."""
        assert REDDIT_COLUMNS.text_column == CANONICAL_TEXT_COLUMN

    def test_original_platform_comment_text_stays_on_body(self) -> None:
        """Raw and preprocessed Reddit comments keep original ``body``."""
        assert REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN == "body"
