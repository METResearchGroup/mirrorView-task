"""One-shot prompting: original+mirror input (large model).

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/one_shot/original_plus_mirror/large/train.py
"""

from __future__ import annotations

from experiments.predict_keep_remove_2026_07_01.models.llm_api.dataset import SupportExample


SYSTEM_PROMPT = """You are a classification assistant for MirrorView keep/remove decisions.

Task:
You will see:
- an original social media post
- a mirrored version of the post (same topic/intensity; flipped political stance)

Decide whether the participant would choose to REMOVE or KEEP the post pair.

Decision labels:
- Output "remove" if the participant would remove the post pair.
- Output "keep" if the participant would keep the post pair.

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
    mirror = mirror_text or ""
    _ = input_mode
    return f"""Original post:
{original_text}

Mirrored post:
{mirror}

Decide: keep or remove?
"""


def render_user_prompt_few_shot(
    *,
    original_text: str,
    mirror_text: str | None,
    input_mode: str,
    support_examples: list[SupportExample],
) -> str:
    mirror = mirror_text or ""
    _ = input_mode

    exemplars = []
    for i, ex in enumerate(support_examples, start=1):
        exemplars.append(
            f"""Example {i}
Original post:
{ex.original_text}

Mirrored post:
{ex.mirror_text}

Decision: {ex.decision}
"""
        )

    exemplars_blob = "\n".join(exemplars).strip()
    return f"""Here are labeled examples.

{exemplars_blob}

Now classify the following post pair:
Original post:
{original_text}

Mirrored post:
{mirror}

Decide: keep or remove?
"""

