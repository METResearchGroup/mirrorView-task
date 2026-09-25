"""Tests for jev_baseline.run ablation registry."""

from __future__ import annotations

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_baseline.run import resolve_ablation
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import VIEW_ORIGINAL, VIEW_PAIR


class TestResolveAblation:
    """Tests for resolve_ablation function."""

    def test_a2_original_only(self):
        """A2 uses original view without feature addendum."""
        config = resolve_ablation("A2_original_only")

        assert config.view == VIEW_ORIGINAL
        assert config.add_criteria is False

    def test_a4_pair_features_addendum(self):
        """A4 uses pair view with feature addendum."""
        config = resolve_ablation("A4_pair_features_addendum")

        assert config.view == VIEW_PAIR
        assert config.add_criteria is True

    def test_unknown_ablation_raises(self):
        """Unknown ablation ids raise ValueError."""
        with pytest.raises(ValueError):
            resolve_ablation("A9_unknown")

    def test_union_source_uses_outputs_union_and_wandb_suffix(self):
        """Union cohort runs write under outputs_union with _union Wandb name."""
        config = resolve_ablation("A1_pair_study_prompt", cohort_source="union")

        assert config.output_dir.name == "A1_pair_study_prompt"
        assert config.output_dir.parent.name == "outputs_union"
        assert config.wandb_name == "A1_pair_study_prompt_union"
        assert config.wandb_group == "jev_baseline_union"
