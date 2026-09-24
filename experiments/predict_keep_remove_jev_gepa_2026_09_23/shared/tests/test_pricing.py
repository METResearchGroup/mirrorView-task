"""Tests for Jev pricing helpers."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.pricing import estimate_jev_cost_usd


class TestEstimateJevCostUsd:
    """Tests for estimate_jev_cost_usd."""

    def test_one_million_input_tokens(self) -> None:
        result = estimate_jev_cost_usd(1_000_000, 0)
        assert result == 0.042

    def test_output_tokens_are_free(self) -> None:
        result = estimate_jev_cost_usd(0, 1_000_000)
        assert result == 0.0
