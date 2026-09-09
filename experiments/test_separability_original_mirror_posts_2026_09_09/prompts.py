"""System and user prompts for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    FIRST_TEXT_COLUMN,
    SECOND_TEXT_COLUMN,
)

USER_PROMPT_TEMPLATE = """Post first:
{first_text}

Post second:
{second_text}
"""

SYSTEM_PROMPT = """You will receive two social media posts. Exactly one post was written by a human. The other post was written by an AI as a political mirror of the human post. Return which presented post is human (first or second) and a one-sentence reason."""


def separability_system_prompt() -> str:
    """Return the system prompt for separability labeling."""
    return SYSTEM_PROMPT


def format_user_prompt(first_text: str, second_text: str) -> str:
    """Interpolate the user message for one presentation pair."""
    raise NotImplementedError
