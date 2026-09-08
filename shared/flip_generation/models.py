"""Pydantic models and result types for flip generation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

FLIP_PARQUET_COLUMNS = (
    "record_id",
    "original_text",
    "llm_toxicity_tier",
    "political_stance",
    "mirrored_text",
    "explanation",
    "label_timestamp",
)


class FlipLlmOutput(BaseModel):
    """Structured Bedrock output for one flip."""

    model_config = ConfigDict(extra="forbid")

    flipped_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)


class FlipEngineRow(BaseModel):
    """One labeled row returned by the Bedrock engine."""

    source_record_id: str
    label_timestamp: str
    flipped_text: str
    explanation: str


class FlipRow(BaseModel):
    """One persisted flip row joined to the input table."""

    model_config = ConfigDict(extra="forbid")

    record_id: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    llm_toxicity_tier: str = Field(min_length=1)
    political_stance: Literal["left", "right"]
    mirrored_text: str = Field(min_length=1)
    explanation: str = Field(min_length=1)
    label_timestamp: str = Field(min_length=1)


@dataclass(frozen=True)
class FlipRunResult:
    """Summary of one flip-generation run."""

    run_prefix: str
    part_count: int
    row_count: int
    failed_count: int
    final_key: str
    wrote_final: bool
