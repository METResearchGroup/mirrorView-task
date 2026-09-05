"""LLM feature: classify toxicity as low, medium, or high.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/llm_toxicity_tiered/generate_feature.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from lib.timestamp_utils import get_current_timestamp
from ml_tooling.llm.llm import structured_chat_completion

SYSTEM_PROMPT = ""

ToxicityTier = Literal["low", "medium", "high"]


class LlmToxicityTieredOutputModel(BaseModel):
    toxicity_tier: ToxicityTier = Field(
        description="Toxicity of the text: low, medium, or high."
    )


class LlmToxicityTieredModel(BaseModel):
    source_record_id: str
    label_timestamp: str
    toxicity_tier: ToxicityTier


def generate_feature(uri: str, text: str) -> LlmToxicityTieredModel:
    """Classify the toxicity tier of post text.

    Parameters
    ----------
    uri
        Record id stored as ``source_record_id``.
    text
        Post text to classify.

    Returns
    -------
    LlmToxicityTieredModel
        Row with the record id, timestamp, and toxicity tier.
    """
    raise NotImplementedError


if __name__ == "__main__":
    samples = [
        ("at://example/post/1", "Thanks for the thoughtful discussion everyone."),
        ("at://example/post/2", "That take is pretty rude, but I see your point."),
        ("at://example/post/3", "You are worthless garbage and should disappear."),
    ]
    for uri, text in samples:
        print(generate_feature(uri, text).model_dump())
