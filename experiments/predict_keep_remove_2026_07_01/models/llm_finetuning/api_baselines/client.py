"""Bedrock client factory for keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

from langchain_aws import ChatBedrockConverse

from lib.constants import BEDROCK_REGION


def get_llm(*, bedrock_model_id: str, temperature: float = 0.0) -> ChatBedrockConverse:
    """Create a LangChain ChatBedrockConverse client for structured inference."""
    return ChatBedrockConverse(
        model=bedrock_model_id,
        region_name=BEDROCK_REGION,
        temperature=temperature,
    )
