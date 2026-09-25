"""Tests for jev_gepa_rebuilt.constants."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    COHORT_UNION_PARQUET,
    DEFAULT_MAX_METRIC_CALLS,
    STUDY_COMPONENT_KEY,
    WANDB_GROUP,
)


class TestRebuiltConstants:
    """Tests for rebuilt GEPA constants."""

    def test_pinned_values_and_cohort_path(self) -> None:
        """Verifies Wandb group, budgets, study key, and union parquet path."""
        assert WANDB_GROUP == "jev_gepa_rebuilt"
        assert DEFAULT_MAX_METRIC_CALLS == 30000
        assert STUDY_COMPONENT_KEY == "study_instruction"
        assert str(COHORT_UNION_PARQUET).endswith("cohort_union_splits.parquet")
