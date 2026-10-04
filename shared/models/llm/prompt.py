"""Study 2 keep/remove prompt for LoRA fine-tuning.

The user template asks for ``keep`` or ``remove`` only. ``{ADD_KEEP_REMOVE_FEATURES_ADDENDUM}``
is left for the caller to fill; the Study 2 unanimous trainer passes an empty string.
"""

from __future__ import annotations

SYSTEM_CONTENT = (
    "You are a content-moderation assistant. "
    "Answer with exactly keep or remove."
)

STUDY_PROMPT_TEMPLATE = """We are developing a new social media platform designed specifically for political discussion. As part of this process, we'd like to understand how people think content on their platform should be moderated. Your task will be to review a series of pairs of real political social media posts, and decide whether both posts in the pair should be allowed or removed from the platform.


The pairs are political mirrors of each other. This means that the mirror text recreates the original message from the opposite political stance. For example:

Original Text:
I'm a bleeding-heart liberal, and I think the issue of abortion is obviously about protecting women's rights!

Mirror Text:
I'm a staunch conservative, and abortion is fully about the sanctity of human life before birth!

Notice that the mirror text changes the core message to match that of the opposite political stance. In other words, the mirror text is not a response to the original text - it replicates the original message as if written from the opposite political stance.

Your job is to decide whether both posts in the pair should be allowed or removed from the platform.

When making your decisions, consider generally whether a post contributes to a healthy environment for political discussion, or whether it would be unhealthy for political discussion. Your goal is to evaluate the messages, using your own judgment.

{ADD_KEEP_REMOVE_FEATURES_ADDENDUM}

Post 1: {post_1_text}

Post 2: {post_2_text}

Answer with exactly keep or remove."""
