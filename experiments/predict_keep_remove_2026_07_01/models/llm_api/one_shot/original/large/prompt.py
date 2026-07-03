"""One-shot prompting: original-only input (large model).

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/one_shot/original/large/train.py
"""

from __future__ import annotations

from experiments.predict_keep_remove_2026_07_01.models.llm_api.dataset import SupportExample


SYSTEM_PROMPT = """You are a classification assistant for MirrorView keep/remove decisions.

Task:
Given a social media post, decide whether the participant would choose to REMOVE or KEEP it.

Decision labels:
- Output "remove" if the participant would remove the post.
- Output "keep" if the participant would keep the post.

Also provide:
- remove_probability: a number in [0,1] representing your confidence that the decision is "remove".

Follow conservative judgment:
- If the text is ambiguous, prefer "keep".
Only use the provided text; do not infer hidden context.
"""


def render_user_prompt_one_shot(
    *,
    original_text: str,
    mirror_text: str | None,
    input_mode: str,
) -> str:
    _ = mirror_text, input_mode  # unused for original-only
    return f"""Post:
{original_text}

Decide: keep or remove?
"""


def render_user_prompt_few_shot(
    *,
    original_text: str,
    mirror_text: str | None,
    input_mode: str,
    support_examples: list[SupportExample],
) -> str:
    _ = mirror_text, input_mode  # unused for original-only

    exemplars = []
    for i, ex in enumerate(support_examples, start=1):
        exemplars.append(
            f"""Example {i}
Post:
{ex.original_text}
Decision: {ex.decision}
"""
        )

    exemplars_blob = "\n".join(exemplars).strip()
    return f"""Here are labeled examples.

{exemplars_blob}

Now classify the following post:
Post:
{original_text}

Decide: keep or remove?
"""

