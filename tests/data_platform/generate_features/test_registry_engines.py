"""Tests that the feature registry runs LLM features on the OpenAI Batch engine."""

from __future__ import annotations

import pytest

from data_platform.generate_features.engines import ENGINE_BUILDERS
from data_platform.generate_features.registry import FEATURE_REGISTRY

LLM_FEATURE_NAMES = (
    "is_news_or_opinion",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
)


@pytest.mark.parametrize("feature_name", LLM_FEATURE_NAMES)
def test_llm_features_use_openai_engine(feature_name: str) -> None:
    """Given the registry, when reading an LLM feature, then its engine is openai."""
    assert FEATURE_REGISTRY[feature_name].engine_type == "openai"


def test_no_registry_feature_uses_langchain() -> None:
    """Given the registry, when listing engines, then none of them is langchain."""
    engines = {spec.engine_type for spec in FEATURE_REGISTRY.values()}

    assert "langchain" not in engines


def test_perspective_feature_stays_on_thread_pool() -> None:
    """Given the registry, when reading the Perspective feature, then it stays thread_pool."""
    assert FEATURE_REGISTRY["is_toxic_tiered"].engine_type == "thread_pool"


def test_every_registry_engine_has_a_builder() -> None:
    """Given the registry, when building each feature, then a builder exists for its engine."""
    for spec in FEATURE_REGISTRY.values():
        assert spec.engine_type in ENGINE_BUILDERS


def test_openai_features_carry_prompt_and_schema() -> None:
    """Given an openai feature, when reading its spec, then prompt and schema are set."""
    for spec in FEATURE_REGISTRY.values():
        if spec.engine_type != "openai":
            continue
        assert spec.system_prompt is not None
        assert spec.llm_output_schema is not None
