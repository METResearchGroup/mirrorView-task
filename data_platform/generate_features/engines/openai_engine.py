"""OpenAI Batch API engine for LLM feature labeling."""

from __future__ import annotations

from collections.abc import Callable

from data_platform.generate_features.engines.base import BaseBatchExecutionEngine
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec, LabelTask


class OpenAIBatchEngine(BaseBatchExecutionEngine):
    """Label tasks through the OpenAI Batch API with structured outputs."""

    def __init__(
        self,
        spec: FeatureSpec,
        run_config: FeatureRunConfig,
        client: object,
        engine_config: object,
        sleep_fn: Callable[[float], None],
        monotonic_fn: Callable[[], float],
    ) -> None:
        super().__init__(spec, run_config)
        raise NotImplementedError

    def batch_label_records(self, tasks: list[LabelTask]) -> list[dict]:
        raise NotImplementedError


def create_openai_client() -> object:
    raise NotImplementedError


def build_openai_engine(
    spec: FeatureSpec,
    run_config: FeatureRunConfig,
) -> OpenAIBatchEngine:
    raise NotImplementedError
