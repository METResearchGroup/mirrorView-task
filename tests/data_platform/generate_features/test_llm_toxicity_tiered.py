from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from data_platform.generate_features.llm_toxicity_tiered.generate_feature import (
    SYSTEM_PROMPT,
    LlmToxicityTieredModel,
    LlmToxicityTieredOutputModel,
    generate_feature,
)
from data_platform.generate_features.registry import FEATURE_REGISTRY

FIXED_LABEL_TIMESTAMP = "2026-09-05T00:00:00Z"


class TestFeatureRegistry:
    """Tests for FEATURE_REGISTRY['llm_toxicity_tiered']."""

    def test_includes_llm_toxicity_tiered(self) -> None:
        """The registry exposes the LLM toxicity feature."""
        assert "llm_toxicity_tiered" in FEATURE_REGISTRY

    def test_uses_langchain_prompt_and_schema(self) -> None:
        """The spec is a LangChain feature with prompt and structured output."""
        spec = FEATURE_REGISTRY["llm_toxicity_tiered"]

        assert spec.engine_type == "langchain"
        assert spec.generate_fn is None
        assert spec.system_prompt
        assert spec.llm_output_schema is LlmToxicityTieredOutputModel
        assert spec.model is LlmToxicityTieredModel


class TestGenerateFeature:
    """Tests for generate_feature()."""

    @pytest.mark.parametrize(
        "toxicity_tier",
        ["low", "medium", "high"],
    )
    def test_returns_expected_schema(self, monkeypatch, toxicity_tier: str) -> None:
        """Verifies generate_feature maps the LLM tier onto the persisted row.

        Parameters
        ----------
        toxicity_tier
            Structured-output label returned by the mocked completion.
        """

        class _Result:
            def __init__(self, tier: str) -> None:
                self.toxicity_tier = tier

        fake_structured_chat_completion = MagicMock(return_value=_Result(toxicity_tier))

        monkeypatch.setattr(
            "data_platform.generate_features.llm_toxicity_tiered.generate_feature.structured_chat_completion",
            fake_structured_chat_completion,
        )
        monkeypatch.setattr(
            "data_platform.generate_features.llm_toxicity_tiered.generate_feature.get_current_timestamp",
            lambda: FIXED_LABEL_TIMESTAMP,
        )

        result = generate_feature("at://example/post/1", "sample text")
        expected = LlmToxicityTieredModel(
            source_record_id="at://example/post/1",
            label_timestamp=FIXED_LABEL_TIMESTAMP,
            toxicity_tier=toxicity_tier,
        )

        assert result == expected
        fake_structured_chat_completion.assert_called_once_with(
            user_prompt="sample text",
            output_schema=LlmToxicityTieredOutputModel,
            system_prompt=SYSTEM_PROMPT,
        )
