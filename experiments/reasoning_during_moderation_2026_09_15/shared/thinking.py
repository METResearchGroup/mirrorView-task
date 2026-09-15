"""Count generated token ids inside a thinking span.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_count_thinking_tokens.py
"""

from __future__ import annotations

from typing import Any, Protocol

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
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
    raise NotImplementedError
