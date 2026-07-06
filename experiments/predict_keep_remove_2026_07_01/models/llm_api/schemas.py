"""Structured response schemas for keep/remove prompting.

Run from root: PYTHONPATH=. uv run python experiments/predict_keep_remove_2026_07_01/models/llm_api/summarize_results.py
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class KeepRemoveDecision(BaseModel):
    """Model output for a single example.

    The integer label convention matches existing models:
    - keep_remove_label=0 => keep
    - keep_remove_label=1 => remove
    """

    decision: Literal["keep", "remove"] = Field(
        description="Predicted decision label.",
    )
    remove_probability: float = Field(
        ge=0.0,
        le=1.0,
        description="Probability that the decision is `remove` in [0,1].",
    )

