"""Classify post text as low, medium, or high toxicity with an LLM.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/llm_toxicity_tiered/generate_feature.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm import structured_chat_completion

SYSTEM_PROMPT = """\
You classify the toxicity of short social media text into exactly one category:

- low: civil text with no insults, threats, slurs, or personal attacks. \
Disagreement, jokes, and blunt opinions are low when they do not target a person \
or group with abuse.
- medium: rude, insulting, or hostile text, including mild targeted profanity or \
name-calling, without threats, slurs, dehumanization, or wishes of harm.
- high: severe abuse. Threats, slurs, dehumanization, or language that wishes \
harm or violence.

Use these examples:

Text: "Thanks for explaining the bill. I still disagree, but I see your point."
Toxicity: low

Text: "City council meets Tuesday to discuss the zoning proposal."
Toxicity: low

Text: "That take is pretty stupid. Maybe read the article before posting."
Toxicity: medium

Text: "You're a joke and nobody takes you seriously."
Toxicity: medium

Text: "People like you should be wiped off the map."
Toxicity: high

Text: "Kill yourself, you worthless piece of garbage."
Toxicity: high

Classify the user's text. Return only the structured fields requested.
"""

ToxicityTier = Literal["low", "medium", "high"]


class LlmToxicityTieredOutputModel(BaseModel):
    toxicity_tier: ToxicityTier = Field(
        description="Toxicity of the text, as low, medium, or high."
    )


class LlmToxicityTieredModel(BaseModel):
    source_record_id: str
    label_timestamp: str
    toxicity_tier: ToxicityTier


def generate_feature(uri: str, text: str) -> LlmToxicityTieredModel:
    """Classify how toxic the post text is, as low, medium, or high.

    Parameters
    ----------
    uri
        Record id stored as ``source_record_id``.
    text
        Post text to classify.

    Returns
    -------
    LlmToxicityTieredModel
        The labeled row, with the record id, timestamp, and toxicity level.
    """
    result = structured_chat_completion(
        user_prompt=text,
        output_schema=LlmToxicityTieredOutputModel,
        system_prompt=SYSTEM_PROMPT,
    )
    return LlmToxicityTieredModel(
        source_record_id=uri,
        label_timestamp=get_current_timestamp(),
        toxicity_tier=result.toxicity_tier,
    )


if __name__ == "__main__":
    samples = [
        ("at://example/post/1", "Thanks for the thoughtful discussion everyone."),
        ("at://example/post/2", "That take is pretty rude, but I see your point."),
        ("at://example/post/3", "You are worthless garbage and should disappear."),
    ]
    for uri, text in samples:
        print(generate_feature(uri, text).model_dump())
