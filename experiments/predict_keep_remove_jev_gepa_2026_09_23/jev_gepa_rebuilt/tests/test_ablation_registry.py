"""Tests for production ABLATION_REGISTRY resolution."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEFAULT_MAX_METRIC_CALLS,
    HALF_BUDGET_MAX_METRIC_CALLS,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import (
    ABLATION_REGISTRY,
    resolve_ablation_config,
)


class TestAblationRegistry:
    """Tests for resolve_ablation_config and ABLATION_REGISTRY."""

    def test_r1_gepa_pair_score_mode_and_budget(self) -> None:
        """R1 uses label_certainty and full metric budget."""
        config = resolve_ablation_config("R1_gepa_pair")
        assert config.score_mode == "label_certainty"
        assert config.max_metric_calls == DEFAULT_MAX_METRIC_CALLS

    def test_r5_gepa_original_half_budget_and_reflection_cap(self) -> None:
        """R5 uses half metric budget and reduced reflection cost."""
        config = resolve_ablation_config("R5_gepa_original")
        assert config.max_metric_calls == HALF_BUDGET_MAX_METRIC_CALLS
        assert config.max_reflection_cost == 2.5

    def test_r7_plain_majority_enabled(self) -> None:
        """R7 is registered with plain_majority and full budget."""
        assert "R7_plain_majority" in ABLATION_REGISTRY
        config = resolve_ablation_config("R7_plain_majority")
        assert config.score_mode == "plain_majority"
        assert config.max_metric_calls == DEFAULT_MAX_METRIC_CALLS
