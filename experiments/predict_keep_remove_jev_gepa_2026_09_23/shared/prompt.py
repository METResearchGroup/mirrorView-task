"""Study-faithful prompt rendering for pair, original, and mirror Jev views.

Single-post instruction diff (``render_original_prompt`` / ``render_mirror_prompt``):

- Opening task sentence uses "each post" instead of "pairs" / "both posts in the pair".
- The political-mirror example block (abortion Original Text / Mirror Text) is omitted.
- Job sentence uses "the post" instead of "both posts in the pair".
- Only one post block labeled ``Post 1:`` is rendered (no ``Post 2:``).
- Healthy-environment and no-right-or-wrong paragraphs are unchanged.
- ``Click Next to continue`` is never included.
"""

from __future__ import annotations

from typesafe_sdk import Noul

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)

POSTS_STATE_KEY = "posts"
QUESTION_ID_PREFIX = "post_"
CLOSING_LINE = "Allow or Remove?"
POST_1_LABEL = "Post 1:"
POST_2_LABEL = "Post 2:"
VIEW_PAIR = "pair"
VIEW_ORIGINAL = "original"
VIEW_MIRROR = "mirror"

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

STUDY_INSTRUCTION_SINGLE = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of real political social media posts, and decide whether each post should be allowed or removed from the platform.

Your job is to decide whether the post should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

There are no right or wrong answers - we are interested in what you personally think."""


def _ordered_texts(
    original_text: str, mirror_text: str, post_1_role: str
) -> tuple[str, str]:
    """Map stored post_1_role to Post 1 and Post 2 text without reshuffling."""
    raise NotImplementedError


def render_pair_prompt(
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool = False,
) -> str:
    """Return full Jev state text for the pair view (A1 or A4 when add_criteria=True).

    Insert KEEP_REMOVE_FEATURES_ADDENDUM after the judgment paragraph and before Post 1
    when add_criteria. Closing line is exactly CLOSING_LINE.
    """
    raise NotImplementedError


def render_original_prompt(original_text: str) -> str:
    """Return Jev state text for original-only view (A2). One post body, no Post 2 block."""
    raise NotImplementedError


def render_mirror_prompt(mirror_text: str) -> str:
    """Return Jev state text for mirror-only view (A3). One post body, no Post 2 block."""
    raise NotImplementedError


def render_state_text(
    view: str,
    original_text: str,
    mirror_text: str,
    post_1_role: str,
    add_criteria: bool = False,
) -> str:
    """Dispatch pair|original|mirror. Raise ValueError on unknown view."""
    raise NotImplementedError


def build_noul_instruction(index: int, view: str) -> str:
    """Return per-question instruction referencing POSTS_STATE_KEY[index]."""
    raise NotImplementedError


def build_questions(n_posts: int, view: str) -> dict[str, Noul]:
    """Return {post_i: Noul(instructions=build_noul_instruction(i, view))} for i in 0..n_posts-1."""
    raise NotImplementedError
