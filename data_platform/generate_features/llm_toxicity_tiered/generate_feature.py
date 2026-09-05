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
    pass


class LlmToxicityTieredModel(BaseModel):
    pass


def generate_feature(uri: str, text: str) -> LlmToxicityTieredModel:
    """Classify the toxicity tier of post text."""
    raise NotImplementedError


if __name__ == "__main__":
    samples = [
        ("at://example/post/1", "Thanks for the thoughtful discussion everyone."),
        ("at://example/post/2", "That take is pretty rude, but I see your point."),
        ("at://example/post/3", "You are worthless garbage and should disappear."),
    ]
    for uri, text in samples:
        print(generate_feature(uri, text).model_dump())
