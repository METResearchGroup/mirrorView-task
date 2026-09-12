"""Pydantic models and expansion helpers for remove-index labeling."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data_platform.generate_features.models import FeatureSpec
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import (
    STUDY_SYSTEM_PROMPT,
)

FEATURE_NAME = "remove_indexes"


class LlmRemoveIndexesModel(BaseModel):
    """Structured LLM output for remove-index labeling."""

    model_config = ConfigDict(extra="forbid")

    remove_pair_indexes: list[int] = Field(default_factory=list)


class RemoveIndexesRow(BaseModel):
    """Persisted remove-index label row."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    label_timestamp: str
    remove_pair_indexes: list[int]


def remove_indexes_spec(engine_type: Literal["openai", "bedrock"]) -> FeatureSpec:
    """Return the FeatureSpec for one labeling engine."""
    return FeatureSpec(
        name=FEATURE_NAME,
        model=RemoveIndexesRow,
        engine_type=engine_type,
        system_prompt=STUDY_SYSTEM_PROMPT,
        llm_output_schema=LlmRemoveIndexesModel,
    )


def expand_remove_indexes(remove_pair_indexes: list[int]) -> list[int]:
    """Expand 1-indexed pair numbers into length-20 binary predictions."""
    raise NotImplementedError
