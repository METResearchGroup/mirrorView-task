"""System and user prompts for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

USER_PROMPT_TEMPLATE = """Post first:
{first_text}

Post second:
{second_text}
"""

SYSTEM_PROMPT = """You will receive two social media posts. Exactly one post was written by a human. The other post was written by an AI as a political mirror of the human post. Return which presented post is human (first or second) and a one-sentence reason."""


def separability_system_prompt() -> str:
    """Return the system prompt for separability labeling.

    Returns
    -------
    str
        Fixed system prompt for both engines.
    """
    return SYSTEM_PROMPT


def format_user_prompt(first_text: str, second_text: str) -> str:
    """Interpolate the user message for one presentation pair.

    Parameters
    ----------
    first_text
        Text shown as the first post.
    second_text
        Text shown as the second post.

    Returns
    -------
    str
        User message sent to the model.
    """
    return USER_PROMPT_TEMPLATE.format(
        first_text=first_text,
        second_text=second_text,
    )
