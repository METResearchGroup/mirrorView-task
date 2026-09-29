"""OpenAI Batch helpers shared across GPT-5.6 Terra experiment steps."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from data_platform.generate_features.engines.openai_engine import (
    OpenAIBatchClient,
    OpenAIBatchEngine,
)
from data_platform.generate_features.models import FeatureSpec, LabelTask
from pydantic import BaseModel


@dataclass(frozen=True)
class RequestUsage:
    source_record_id: str
    input_tokens: int
    output_tokens: int


@dataclass(frozen=True)
class BatchRun:
    rows: list[dict]
    usage: list[RequestUsage]
    wall_seconds: float


def build_feature_spec(
    name: str,
    row_model: type[BaseModel],
    system_prompt: str,
    output_schema: type[BaseModel],
) -> FeatureSpec:
    raise NotImplementedError


def build_engine(spec: FeatureSpec, client: OpenAIBatchClient) -> OpenAIBatchEngine:
    raise NotImplementedError


def parse_request_usage(output_text: str, ordered_ids: list[str]) -> list[RequestUsage]:
    raise NotImplementedError


def run_batch(
    engine: OpenAIBatchEngine,
    client: OpenAIBatchClient,
    tasks: list[LabelTask],
    clock: Callable[[], float],
) -> BatchRun:
    raise NotImplementedError
