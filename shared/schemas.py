"""Structured response schemas for prompt-tuning keep/remove runs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class IsRemoveResult(BaseModel):
    """Model output for a single linked-fate pair."""

    is_remove: bool = Field(
        description="True if both posts in the pair should be removed.",
    )
