"""Study-linked-fate prompt with blinded Post 1/Post 2 shuffle.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

STUDY_PROMPT_TEMPLATE = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.


The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.


Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

Post 1: {post_1_text}

Post 2: {post_2_text}

Allow Or Remove?"""


def _should_swap_posts(*, message_id: str, seed: int) -> bool:
    return (hash((message_id, seed)) % 2) == 1


def render_user_prompt(
    *,
    original_text: str,
    mirror_text: str,
    message_id: str,
    seed: int,
) -> str:
    """Render the study prompt with deterministic Post 1/Post 2 shuffle."""
    if _should_swap_posts(message_id=message_id, seed=seed):
        post_1_text = mirror_text
        post_2_text = original_text
    else:
        post_1_text = original_text
        post_2_text = mirror_text
    return STUDY_PROMPT_TEMPLATE.format(
        post_1_text=post_1_text,
        post_2_text=post_2_text,
    )
