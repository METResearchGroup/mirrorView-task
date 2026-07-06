"""Variant registry for Bedrock zero-shot keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BedrockVariant:
    variant_slug: str
    folder: str
    bedrock_model_id: str
    display_name: str


VARIANTS: tuple[BedrockVariant, ...] = (
    BedrockVariant(
        variant_slug="ministral_3_8b_instruct",
        folder="ministral-3-8b-instruct",
        bedrock_model_id="mistral.ministral-3-8b-instruct",
        display_name="Ministral 3 8B Instruct",
    ),
    BedrockVariant(
        variant_slug="ministral_3_14b_instruct",
        folder="ministral-3-14b-instruct",
        bedrock_model_id="mistral.ministral-3-14b-instruct",
        display_name="Ministral 3 14B Instruct",
    ),
    BedrockVariant(
        variant_slug="qwen3_32b",
        folder="qwen3-32b",
        bedrock_model_id="qwen.qwen3-32b-v1:0",
        display_name="Qwen3 32B",
    ),
    BedrockVariant(
        variant_slug="qwen3_next_80b_a3b",
        folder="qwen3-next-80b-a3b",
        bedrock_model_id="qwen.qwen3-next-80b-a3b",
        display_name="Qwen3 Next 80B A3B",
    ),
)

VARIANT_BY_SLUG: dict[str, BedrockVariant] = {v.variant_slug: v for v in VARIANTS}
