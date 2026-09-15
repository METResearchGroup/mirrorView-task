"""Render the linked-fate study prompt for one original/mirror pair.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/experiment1/run.py --smoke --limit 3
"""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    CLOSING_LINE,
    POST_1_LABEL,
    POST_2_LABEL,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)

STUDY_INSTRUCTION = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.

The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.

Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

There are no right or wrong answers - we are interested in what you personally think."""


def render_prompt(
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool,
) -> str:
    """Return the user message for one linked-fate pair."""
    post_1_text, post_2_text = _ordered_texts(original_text, mirror_text, post_1_role)
    addendum = KEEP_REMOVE_FEATURES_ADDENDUM if add_criteria else ""
    return (
        f"{STUDY_INSTRUCTION}{addendum}\n\n"
        f"{POST_1_LABEL} {post_1_text}\n\n"
        f"{POST_2_LABEL} {post_2_text}\n\n"
        f"{CLOSING_LINE}"
    )


def _ordered_texts(
    original_text: str, mirror_text: str, post_1_role: str
) -> tuple[str, str]:
    role_text = {ROLE_ORIGINAL: original_text, ROLE_MIRROR: mirror_text}
    post_1_text = role_text[post_1_role]
    post_2_role = ROLE_MIRROR if post_1_role == ROLE_ORIGINAL else ROLE_ORIGINAL
    return post_1_text, role_text[post_2_role]
