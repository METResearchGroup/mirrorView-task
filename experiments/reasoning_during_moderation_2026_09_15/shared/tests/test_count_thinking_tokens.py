"""Tests for count_thinking_tokens()."""

from __future__ import annotations

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    STATUS_EMPTY_THINKING,
    STATUS_MISSING_CLOSE_TAG,
    STATUS_TRUNCATED,
    STATUS_VALID,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.thinking import (
    count_thinking_tokens,
)

OPEN_ID = 1
CLOSE_ID = 2
MAX_NEW_TOKENS = 4


class FakeTokenizer:
    """Maps think tags to single token ids."""

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        mapping = {"<think>": [OPEN_ID], "</think>": [CLOSE_ID]}
        return mapping[text]


class TestCountThinkingTokens:
    """Tests for count_thinking_tokens function."""

    def test_counts_ids_between_tags(self) -> None:
        """Verifies valid status and a count of two inner ids."""
        generated_ids = [OPEN_ID, 11, 12, CLOSE_ID, 99]
        expected = 2

        result = count_thinking_tokens(
            generated_ids, FakeTokenizer(), MAX_NEW_TOKENS
        )

        assert result.status == STATUS_VALID
        assert result.thinking_token_count == expected

    def test_empty_thinking_when_tags_touch(self) -> None:
        """Verifies empty_thinking when open is followed by close."""
        generated_ids = [OPEN_ID, CLOSE_ID]

        result = count_thinking_tokens(
            generated_ids, FakeTokenizer(), MAX_NEW_TOKENS
        )

        assert result.status == STATUS_EMPTY_THINKING
        assert result.thinking_token_count == 0

    def test_truncated_without_close_at_cap(self) -> None:
        """Verifies truncated when output length equals max_new_tokens."""
        generated_ids = [OPEN_ID, 11, 12, 13]

        result = count_thinking_tokens(
            generated_ids, FakeTokenizer(), MAX_NEW_TOKENS
        )

        assert result.status == STATUS_TRUNCATED

    def test_missing_close_when_short(self) -> None:
        """Verifies missing_close_tag when output is shorter than the cap."""
        generated_ids = [OPEN_ID, 11]

        result = count_thinking_tokens(
            generated_ids, FakeTokenizer(), MAX_NEW_TOKENS
        )

        assert result.status == STATUS_MISSING_CLOSE_TAG

    def test_counts_from_start_without_open_tag(self) -> None:
        """Verifies ids before a close tag count when open is absent."""
        generated_ids = [11, 12, CLOSE_ID]
        expected = 2

        result = count_thinking_tokens(
            generated_ids, FakeTokenizer(), MAX_NEW_TOKENS
        )

        assert result.status == STATUS_VALID
        assert result.thinking_token_count == expected
