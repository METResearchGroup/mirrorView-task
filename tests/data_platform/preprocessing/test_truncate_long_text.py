"""Tests for truncate_long_text and its preprocess plugin wiring.

given empty or whitespace-only text
when truncate_long_text runs
then the result is an empty string

given short complete-sentence text
when truncate_long_text runs
then the text is unchanged

given long English text with sentence boundaries inside the 320-char window
when truncate_long_text runs
then the result is the last complete sentence that fits

given long text with no sentence or line boundary
when truncate_long_text runs
then the result is a word cut at MAX_CHARS, or a hard cut when there is no space

given a preprocess spec that lists truncate_long_text
when apply_text_transform runs
then the standardized text column is truncated and other columns stay the same
"""

from __future__ import annotations

from dataclasses import replace

import pandas as pd
import pytest

from data_platform.preprocessing.preprocess_bluesky import BLUESKY_SPEC
from data_platform.preprocessing.preprocess_reddit import REDDIT_SPEC
from data_platform.preprocessing.preprocess_twitter import TWITTER_SPEC
from data_platform.preprocessing.runner import apply_text_transform
from data_platform.preprocessing.truncate_long_text import (
    MAX_CHARS,
    SENTENCE_OVERFLOW,
    truncate_long_text,
)
from data_platform.preprocessing.validators.twitter_validators import strip_tco_links
from data_platform.utils.platform_specific_columns import STANDARDIZED_TEXT_COLUMN
from tests.data_platform.constants import (
    EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT,
    LONG_ENGLISH_TEXT,
)


class TestTruncateLongText:
    """Tests for truncate_long_text()."""

    def test_empty_string_stays_empty(self) -> None:
        """Empty input stays empty."""
        expected = ""

        result = truncate_long_text("")

        assert result == expected

    def test_whitespace_only_becomes_empty(self) -> None:
        """Whitespace-only input strips to an empty string."""
        expected = ""

        result = truncate_long_text("   \n  ")

        assert result == expected

    def test_short_complete_sentence_is_unchanged(self) -> None:
        """Text under the cap that already ends as a complete sentence is kept."""
        text = "This is a complete sentence."
        expected = text

        result = truncate_long_text(text)

        assert result == expected

    def test_short_incomplete_sentence_is_unchanged(self) -> None:
        """Short text with no usable cut stays as-is when it is under the cap."""
        text = "This is not finished"
        expected = text

        result = truncate_long_text(text)

        assert result == expected

    def test_decimal_period_is_not_treated_as_a_sentence_end(self) -> None:
        """A version number such as 2.0 does not count as a sentence boundary."""
        text = "Reconstruction 2.0 is underway now."
        expected = text

        result = truncate_long_text(text)

        assert result == expected

    def test_long_text_cuts_at_last_complete_sentence_in_window(self) -> None:
        """Long text keeps the last complete sentence that fits in the overflow window."""
        head = "First complete sentence. Second complete sentence."
        text = head + (" word" * 80) + " Third complete sentence. trailing fragment"
        expected = head

        result = truncate_long_text(text)

        assert result == expected

    def test_overflow_window_keeps_a_sentence_that_ends_just_past_the_cap(
        self,
    ) -> None:
        """A sentence that ends between MAX_CHARS and MAX_CHARS plus overflow is kept."""
        prefix = ("C" * 309) + "."
        text = prefix + " more incomplete text without a finish"
        expected = prefix
        assert MAX_CHARS < len(prefix) <= MAX_CHARS + SENTENCE_OVERFLOW

        result = truncate_long_text(text)

        assert result == expected

    def test_paragraph_break_is_used_when_later_text_is_incomplete(self) -> None:
        """A complete first paragraph is kept when the rest has no sentence end."""
        first_paragraph = "This is a complete sentence on line one."
        text = first_paragraph + "\n\n" + ("more filler words without a period " * 20)
        expected = first_paragraph

        result = truncate_long_text(text)

        assert result == expected

    def test_word_boundary_fallback_when_there_is_no_sentence(self) -> None:
        """Text with no sentence end is cut at the last space at or before MAX_CHARS."""
        words = (
            "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo "
            "lima mike november oscar papa quebec romeo sierra tango uniform "
            "victor whiskey xray yankee zulu "
        )
        text = words * 8
        expected = (
            "alpha bravo charlie delta echo foxtrot golf hotel india juliet kilo "
            "lima mike november oscar papa quebec romeo sierra tango uniform "
            "victor whiskey xray yankee zulu alpha bravo charlie delta echo "
            "foxtrot golf hotel india juliet kilo lima mike november oscar papa "
            "quebec romeo sierra tango uniform"
        )

        result = truncate_long_text(text)

        assert result == expected
        assert len(result) <= MAX_CHARS

    def test_hard_cut_when_there_is_no_space(self) -> None:
        """A single token longer than the cap is cut at MAX_CHARS."""
        text = "x" * 400
        expected = "x" * MAX_CHARS

        result = truncate_long_text(text)

        assert result == expected

    def test_repeated_english_sentences_match_truncation_v3(self) -> None:
        """The shared long-English fixture truncates to three complete sentences."""
        expected = EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT

        result = truncate_long_text(LONG_ENGLISH_TEXT)

        assert result == expected
        assert len(LONG_ENGLISH_TEXT) > MAX_CHARS


class TestApplyTextTransformWithTruncateLongText:
    """Tests that apply_text_transform() runs truncate_long_text as a plugin."""

    def test_truncates_standardized_text_and_keeps_original_body(self) -> None:
        """Reddit rows get truncated text while the original body column stays."""
        spec = replace(REDDIT_SPEC, text_transforms=(truncate_long_text,))
        records = pd.DataFrame(
            [
                {
                    STANDARDIZED_TEXT_COLUMN: LONG_ENGLISH_TEXT,
                    "body": LONG_ENGLISH_TEXT,
                    "comment_fullname": "t1_keep",
                }
            ]
        )
        expected_text = EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT

        result = apply_text_transform(records, spec)

        assert result.iloc[0][STANDARDIZED_TEXT_COLUMN] == expected_text
        assert result.iloc[0]["body"] == LONG_ENGLISH_TEXT
        assert records.iloc[0][STANDARDIZED_TEXT_COLUMN] == LONG_ENGLISH_TEXT

    def test_strips_tco_links_before_truncating_twitter_text(self) -> None:
        """Twitter plugins run in order: t.co URLs are removed, then text is truncated."""
        spec = replace(
            TWITTER_SPEC,
            text_transforms=(strip_tco_links, truncate_long_text),
        )
        text = LONG_ENGLISH_TEXT + " https://t.co/abc123"
        records = pd.DataFrame([{STANDARDIZED_TEXT_COLUMN: text}])
        expected = EXPECTED_TRUNCATED_LONG_ENGLISH_TEXT

        result = apply_text_transform(records, spec)

        assert result.iloc[0][STANDARDIZED_TEXT_COLUMN] == expected
        assert "t.co" not in result.iloc[0][STANDARDIZED_TEXT_COLUMN]


class TestPreprocessSpecsIncludeTruncateLongText:
    """Tests that each platform spec plugs in truncate_long_text."""

    @pytest.mark.parametrize(
        "spec",
        [BLUESKY_SPEC, REDDIT_SPEC, TWITTER_SPEC],
        ids=["bluesky", "reddit", "twitter"],
    )
    def test_spec_lists_truncate_long_text(self, spec) -> None:
        """Every platform runs truncate_long_text during integration-specific preprocessing."""
        assert truncate_long_text in spec.text_transforms
