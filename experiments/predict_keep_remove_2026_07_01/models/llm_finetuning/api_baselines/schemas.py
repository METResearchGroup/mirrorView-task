"""Structured response schemas for Bedrock keep/remove baselines.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_finetuning/api_baselines/summarize_results.py
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class IsRemoveResult(BaseModel):
    """Model output for a single linked-fate pair."""

    is_remove: bool = Field(
        description="True if both posts in the pair should be removed.",
    )
