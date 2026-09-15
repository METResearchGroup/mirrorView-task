"""Count generated token ids inside a thinking span.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_count_thinking_tokens.py
"""

from __future__ import annotations

from typing import Protocol

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    STATUS_EMPTY_THINKING,
    STATUS_MISSING_CLOSE_TAG,
    STATUS_TRUNCATED,
    STATUS_VALID,
    THINK_CLOSE_TAG,
    THINK_OPEN_TAG,
    ThinkingCount,
)


class TokenEncoder(Protocol):
    """Tokenizer that can encode a tag string to token ids."""

    def encode(self, text: str, add_special_tokens: bool = False) -> list[int]:
        """Return token ids for ``text``."""


def count_thinking_tokens(
    generated_ids: list[int],
    tokenizer: TokenEncoder,
    max_new_tokens: int,
) -> ThinkingCount:
    """Count generated ids inside the thinking span, excluding think tags."""
    open_ids = list(tokenizer.encode(THINK_OPEN_TAG, add_special_tokens=False))
    close_ids = list(tokenizer.encode(THINK_CLOSE_TAG, add_special_tokens=False))
    open_at = _find_subsequence(generated_ids, open_ids)
    close_at = _find_subsequence(generated_ids, close_ids)
    if close_at is None:
        return _missing_or_truncated(generated_ids, max_new_tokens)
    start = 0 if open_at is None else open_at + len(open_ids)
    inner = generated_ids[start:close_at]
    status = STATUS_VALID if inner else STATUS_EMPTY_THINKING
    return ThinkingCount(status, len(inner), close_at)


def _missing_or_truncated(
    generated_ids: list[int], max_new_tokens: int
) -> ThinkingCount:
    if len(generated_ids) >= max_new_tokens:
        return ThinkingCount(STATUS_TRUNCATED, 0, None)
    return ThinkingCount(STATUS_MISSING_CLOSE_TAG, 0, None)


def _find_subsequence(haystack: list[int], needle: list[int]) -> int | None:
    if not needle:
        return None
    last_start = len(haystack) - len(needle)
    for start in range(last_start + 1):
        if haystack[start : start + len(needle)] == needle:
            return start
    return None
