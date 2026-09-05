"""Batch execution engine factory."""

from __future__ import annotations

from collections.abc import Callable

from data_platform.generate_features.engines.base import BatchExecutionEngine
from data_platform.generate_features.engines.langchain_engine import LangChainBatchEngine
from data_platform.generate_features.engines.openai_engine import build_openai_engine
from data_platform.generate_features.engines.thread_pool_engine import ThreadPoolBatchEngine
from data_platform.generate_features.models import FeatureRunConfig, FeatureSpec

EngineBuilder = Callable[[FeatureSpec, FeatureRunConfig], BatchExecutionEngine]

ENGINE_BUILDERS: dict[str, EngineBuilder] = {
    "langchain": LangChainBatchEngine,
    "thread_pool": ThreadPoolBatchEngine,
    "openai": build_openai_engine,
}


def build_engine(spec: FeatureSpec, run_config: FeatureRunConfig) -> BatchExecutionEngine:
    """Construct the batch engine implementation declared on the feature spec."""
    builder = ENGINE_BUILDERS.get(spec.engine_type)
    if builder is None:
        raise ValueError(f"Unknown engine_type: {spec.engine_type}")
    return builder(spec, run_config)
