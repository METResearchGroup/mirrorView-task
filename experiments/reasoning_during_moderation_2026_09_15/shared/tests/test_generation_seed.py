"""Tests for generation_seed() and sampling kwargs filtering."""

from __future__ import annotations

from types import SimpleNamespace

from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    QWEN_MIN_P,
    QWEN_PRESENCE_PENALTY,
    QWEN_REPETITION_PENALTY,
    QWEN_TEMPERATURE,
    QWEN_TOP_K,
    QWEN_TOP_P,
    SamplingConfig,
    UINT32_MODULUS,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.runner import (
    _sampling_kwargs,
    generation_seed,
)


class TestGenerationSeed:
    """Tests for generation_seed function."""

    def test_same_post_is_stable_uint32(self) -> None:
        """Verifies two calls match and the seed fits in 32 bits."""
        first = generation_seed("A")
        second = generation_seed("A")

        assert first == second
        assert 0 <= first < UINT32_MODULUS


class TestSamplingKwargs:
    """Tests for generate() sampling kwarg filtering."""

    def test_drops_presence_penalty_when_config_lacks_it(self) -> None:
        """Verifies Qwen presence_penalty is omitted when GenerationConfig has no field."""
        sampling = SamplingConfig(
            QWEN_TEMPERATURE,
            QWEN_TOP_P,
            QWEN_TOP_K,
            QWEN_MIN_P,
            QWEN_PRESENCE_PENALTY,
            QWEN_REPETITION_PENALTY,
        )
        config = SimpleNamespace(
            temperature=1.0,
            top_p=0.95,
            top_k=20,
            min_p=0.0,
            repetition_penalty=1.0,
        )
        kwargs = _sampling_kwargs(sampling, config)
        assert "presence_penalty" not in kwargs
        assert kwargs["temperature"] == QWEN_TEMPERATURE
        assert kwargs["top_k"] == QWEN_TOP_K
        assert kwargs["min_p"] == QWEN_MIN_P
        assert kwargs["repetition_penalty"] == QWEN_REPETITION_PENALTY
