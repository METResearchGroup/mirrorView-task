"""Tests for reflection LM USD estimation."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.pricing import (
    estimate_reflection_cost_usd,
)


class TestReflectionPricing:
    """Tests for estimate_reflection_cost_usd."""

    def test_luna_input_million_tokens(self) -> None:
        """One million input tokens on gpt-6-luna costs 0.10 USD."""
        result = estimate_reflection_cost_usd("openai/gpt-6-luna", 1_000_000, 0)
        assert result == 0.10

    def test_terra_output_million_tokens(self) -> None:
        """One million output tokens on gpt-5.6-terra costs 12.0 USD."""
        result = estimate_reflection_cost_usd("openai/gpt-5.6-terra", 0, 1_000_000)
        assert result == 12.0
