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
    """Label one prepared record through the public Converse helper.

    Parameters
    ----------
    client
        Injected Bedrock runtime client; not constructed here.
    model
        Confirmed registry entry supplying the exact Bedrock model ID.
    record
        One prepared Study 2 input row.
    max_tokens
        Maximum output tokens forwarded to Converse.

    Returns
    -------
    tuple[RemovePrediction, BedrockUsage]
        Validated label and per-call token usage from the engine.

    Raises
    ------
    Exception
        Propagates Bedrock, JSON, or validation errors from ``converse_label``.
    """
    user_text = format_baseline_zero_shot_keep_remove_prompt(
        record.post_1_text,
        record.post_2_text,
    )
    prediction, usage = converse_label(
        client,
        model.model_id,
        EMPTY_SYSTEM_PROMPT,
        RemovePrediction,
        user_text,
        max_tokens,
    )
    return RemovePrediction.model_validate(prediction.model_dump()), usage
