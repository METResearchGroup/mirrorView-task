"""Render the study moderation prompt from post texts and optional feature addendum."""

from __future__ import annotations

from experiments.llm_prompt_engineering_2026_08_05.prompt import (
    KEEP_REMOVE_FEATURES_ADDENDUM,
    STUDY_PROMPT_TEMPLATE,
)


def generate_prompt(
    *,
    post_1_text: str,
    post_2_text: str,
    add_keep_remove_features_addendum: bool = False,
) -> str:
    """Fill STUDY_PROMPT_TEMPLATE with the two posts and optional keep/remove criteria."""
    addendum = KEEP_REMOVE_FEATURES_ADDENDUM if add_keep_remove_features_addendum else ""
    return STUDY_PROMPT_TEMPLATE.format(
        ADD_KEEP_REMOVE_FEATURES_ADDENDUM=addendum,
        post_1_text=post_1_text,
        post_2_text=post_2_text,
    )
