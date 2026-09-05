"""OpenAI Batch API engine for LLM feature labeling."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from data_platform.generate_features.engines.base import BaseBatchExecutionEngine
from data_platform.generate_features.engines.openai_batch import (
    OPENAI_BATCH_ENDPOINT,
    OpenAIBatchTokenUsage,
)
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask
from lib.constants import DEFAULT_LLM_MODEL

OPENAI_BATCH_COMPLETION_WINDOW = "24h"
OPENAI_BATCH_FILE_PURPOSE = "batch"
OPENAI_BATCH_JSONL_FILENAME = "openai_feature_batch.jsonl"
OPENAI_BATCH_TEMPERATURE = 0.0
POLL_INTERVAL_SECONDS = 5.0
POLL_TIMEOUT_SECONDS = 3600.0
BATCH_COMPLETED_STATUS = "completed"
BATCH_FAILED_STATUSES = frozenset(
    {
        "failed",
        "expired",
        "cancelled",
        "cancelling",
    }
)


class OpenAIBatchClient(Protocol):
    """Subset of the OpenAI SDK client used by the Batch engine."""

    files: Any
    batches: Any


@dataclass(frozen=True)
class OpenAIBatchEngineConfig:
    model: str
    temperature: float
    poll_interval_seconds: float
    poll_timeout_seconds: float
    completion_window: str
    endpoint: str


DEFAULT_OPENAI_BATCH_ENGINE_CONFIG = OpenAIBatchEngineConfig(
    model=DEFAULT_LLM_MODEL,
    temperature=OPENAI_BATCH_TEMPERATURE,
    poll_interval_seconds=POLL_INTERVAL_SECONDS,
    poll_timeout_seconds=POLL_TIMEOUT_SECONDS,
    completion_window=OPENAI_BATCH_COMPLETION_WINDOW,
    endpoint=OPENAI_BATCH_ENDPOINT,
)


class OpenAIBatchEngine(BaseBatchExecutionEngine):
    """Label tasks through the OpenAI Batch API with structured outputs."""

    def __init__(
        self,
        spec: FeatureSpec,
        run_config: FeatureRunConfig,
        client: OpenAIBatchClient,
        engine_config: OpenAIBatchEngineConfig,
        sleep_fn: Callable[[float], None],
        monotonic_fn: Callable[[], float],
    ) -> None:
        super().__init__(spec, run_config)
        self._client = client
        self._engine_config = engine_config
        self._sleep_fn = sleep_fn
        self._monotonic_fn = monotonic_fn
        self.last_batch_usage: OpenAIBatchTokenUsage | None = None

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        raise NotImplementedError


def create_openai_client() -> OpenAIBatchClient:
    raise NotImplementedError


def build_openai_engine(
    spec: FeatureSpec,
    run_config: FeatureRunConfig,
) -> OpenAIBatchEngine:
    raise NotImplementedError


def wait_for_completed_batch(
    client: OpenAIBatchClient,
    batch_id: str,
    poll_interval_seconds: float,
    poll_timeout_seconds: float,
    sleep_fn: Callable[[float], None],
    monotonic_fn: Callable[[], float],
) -> Any:
    raise NotImplementedError
