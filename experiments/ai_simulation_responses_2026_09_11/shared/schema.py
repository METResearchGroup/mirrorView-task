"""Pydantic models and expansion helpers for remove-index labeling."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from data_platform.generate_features.models import FeatureSpec
from experiments.ai_simulation_responses_2026_09_11.shared.constants import (
    PAIR_RECORD_SEPARATOR,
    PAIR_YES_NO_FEATURE_NAME,
    POSTS_PER_USER,
)
from experiments.ai_simulation_responses_2026_09_11.shared.prompts import (
    STUDY_SYSTEM_PROMPT,
    STUDY_SYSTEM_PROMPT_SINGLE_PAIR,
)

FEATURE_NAME = "remove_indexes"
YES_REMOVE = "yes"
NO_REMOVE = "no"


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


class LlmPairYesNoModel(BaseModel):
    """Structured LLM output for one-pair yes/no labeling."""

    model_config = ConfigDict(extra="forbid")

    remove: Literal["yes", "no"]


class PairYesNoRow(BaseModel):
    """Persisted one-pair yes/no label row."""

    model_config = ConfigDict(extra="forbid")

    source_record_id: str
    label_timestamp: str
    remove: Literal["yes", "no"]


def pair_yes_no_spec(engine_type: Literal["openai", "bedrock"]) -> FeatureSpec:
    """Return the FeatureSpec for experiment 6 one-pair labeling."""
    return FeatureSpec(
        name=PAIR_YES_NO_FEATURE_NAME,
        model=PairYesNoRow,
        engine_type=engine_type,
        system_prompt=STUDY_SYSTEM_PROMPT_SINGLE_PAIR,
        llm_output_schema=LlmPairYesNoModel,
    )


def pair_record_id(prolific_id: str, pair_index: int) -> str:
    """Return the campaign record id for one user-pair."""
    return f"{prolific_id}{PAIR_RECORD_SEPARATOR}{pair_index}"


def parse_pair_record_id(record_id: str) -> tuple[str, int]:
    """Split a pair campaign id into prolific_id and pair_index."""
    prolific_id, index_text = record_id.rsplit(PAIR_RECORD_SEPARATOR, 1)
    return prolific_id, int(index_text)


def parse_remove_yes_no(value: str) -> int:
    """Return 1 for yes and 0 for no."""
    if value == YES_REMOVE:
        return 1
    if value == NO_REMOVE:
        return 0
    raise ValueError(f"invalid remove value: {value}")


def stitch_pair_predictions(
    rows: list[tuple[str, int, str]],
) -> dict[str, list[int]]:
    """Stitch per-pair yes/no answers into user-level remove indexes."""
    grouped: dict[str, dict[int, str]] = {}
    for prolific_id, pair_index, remove in rows:
        grouped.setdefault(prolific_id, {})[pair_index] = remove
    return {
        prolific_id: indexes
        for prolific_id, answers in grouped.items()
        if (indexes := _complete_remove_indexes(answers)) is not None
    }


def _complete_remove_indexes(answers: dict[int, str]) -> list[int] | None:
    expected = set(range(1, POSTS_PER_USER + 1))
    if set(answers) != expected:
        return None
    indexes: list[int] = []
    for pair_index in range(1, POSTS_PER_USER + 1):
        try:
            if parse_remove_yes_no(answers[pair_index]) == 1:
                indexes.append(pair_index)
        except ValueError:
            return None
    return indexes


def expand_remove_indexes(remove_pair_indexes: list[int]) -> list[int]:
    """Expand 1-indexed pair numbers into length-20 binary predictions."""
    predictions = [0] * 20
    seen: set[int] = set()
    for index in remove_pair_indexes:
        if index < 1 or index > 20:
            raise ValueError(f"pair index out of range: {index}")
        if index in seen:
            raise ValueError(f"duplicate pair index: {index}")
        seen.add(index)
        predictions[index - 1] = 1
    return predictions
