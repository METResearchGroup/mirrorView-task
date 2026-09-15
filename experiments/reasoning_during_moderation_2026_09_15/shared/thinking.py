"""Count generated token ids inside a thinking span.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/reasoning_during_moderation_2026_09_15/shared/tests/test_count_thinking_tokens.py
"""

from __future__ import annotations

from typing import Any


def count_thinking_tokens(
    generated_ids: list[int],
    tokenizer: Any,
    max_new_tokens: int,
) -> Any:
    raise NotImplementedError
