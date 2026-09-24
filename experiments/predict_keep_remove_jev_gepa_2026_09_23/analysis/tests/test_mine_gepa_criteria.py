"""Unit tests for mine_gepa_criteria.py."""

from __future__ import annotations

from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.mine_gepa_criteria import (
    compare_criteria,
    held_out_spot_check,
    normalize_criterion,
    split_into_atomic_criteria,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.analysis.synonyms import SYNONYM_MAP


class TestSplitAtomicCriteria:
    """Tests for split_into_atomic_criteria function."""

    def test_splits_numbered_items(self) -> None:
        prompt = "Intro\n1. First criterion here\n2. Second criterion here"

        result = split_into_atomic_criteria(prompt)

        assert len(result) == 2
        assert "First criterion here" in result[0]
        assert "Second criterion here" in result[1]


class TestNormalizeCriterion:
    """Tests for normalize_criterion function."""

    def test_applies_vulgar_to_profanity_synonym(self) -> None:
        result = normalize_criterion("Contains Vulgar language", SYNONYM_MAP)

        assert "profanity" in result


class TestCompareCriteria:
    """Tests for compare_criteria function."""

    def test_exact_match_after_normalization(self) -> None:
        human = ["remove posts with profanity attacks"]
        gepa = ["remove posts with vulgar attacks"]

        result = compare_criteria(gepa, human, synonyms=SYNONYM_MAP)

        assert bool(result.iloc[0]["exact_or_synonym_match"]) is True


class TestHeldOutSpotCheck:
    """Tests for held_out_spot_check function."""

    def test_reserves_twenty_percent_with_fixed_seed(self) -> None:
        criteria = [f"criterion-{index}" for index in range(10)]

        result = held_out_spot_check(criteria, holdout_fraction=0.2, seed=20260924)

        holdout_rows = result[result["split"] == "holdout"]
        mining_rows = result[result["split"] == "mining"]
        assert len(holdout_rows) == 2
        assert len(mining_rows) == 8
        holdout_set = set(holdout_rows["criterion"])
        mining_set = set(mining_rows["criterion"])
        assert holdout_set.isdisjoint(mining_set)
