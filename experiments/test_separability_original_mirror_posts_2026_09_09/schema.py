"""Pydantic models for separability labeling.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data_platform.generate_features.models import FeatureSpec
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    FEATURE_NAME,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.prompts import (
    separability_system_prompt,
)


class LlmSeparabilityModel(BaseModel):
    """Structured LLM output for separability labeling."""

    model_config = ConfigDict(extra="forbid")

    human_slot: Literal["first", "second"]
    reason: str = Field(min_length=1)


class SeparabilityRow(BaseModel):
    """Persisted separability label row."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    label_timestamp: str
    human_slot: Literal["first", "second"]
    reason: str


def separability_spec(engine_type: Literal["openai", "bedrock"]) -> FeatureSpec:
    """Return the FeatureSpec for one labeling engine.

    Parameters
    ----------
    engine_type
        ``openai`` or ``bedrock``.

    Returns
    -------
    FeatureSpec
        Separability feature definition for the chosen engine.
    """
    return FeatureSpec(
        name=FEATURE_NAME,
        model=SeparabilityRow,
        engine_type=engine_type,
        system_prompt=separability_system_prompt(),
        llm_output_schema=LlmSeparabilityModel,
    )
