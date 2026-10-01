"""Thin Bedrock wrapper for one Study 2 input record."""

from __future__ import annotations

from typing import TYPE_CHECKING

from data_platform.generate_features.engines.bedrock_engine import (
    BedrockRuntimeClient,
    BedrockUsage,
    converse_label,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.prompts import (
    format_baseline_zero_shot_keep_remove_prompt,
)
from experiments.zero_shot_llm_inference_2026_09_30.shared.schemas import (
    ModelDefinition,
    RemovePrediction,
    Study2InputRecord,
)

if TYPE_CHECKING:
    pass

EMPTY_SYSTEM_PROMPT = ""


def label_record(
    client: BedrockRuntimeClient,
    model: ModelDefinition,
    record: Study2InputRecord,
    max_tokens: int,
) -> tuple[RemovePrediction, BedrockUsage]:
    """Label one prepared record through the public Converse helper."""
    raise NotImplementedError
