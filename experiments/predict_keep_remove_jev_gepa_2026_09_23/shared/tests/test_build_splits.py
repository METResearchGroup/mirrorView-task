"""Tests for assign_splits, sample_gepa_subsets, and compute_split_hash."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import (
    SPLIT_SEED,
    assign_splits,
    compute_split_hash,
    sample_gepa_subsets,
)


def _synthetic_cohort(n_rows: int = 100) -> pd.DataFrame:
    stances = ("left", "right")
    toxicities = ("low", "middle", "high")
    rows: list[dict[str, object]] = []
    for index in range(n_rows):
        rows.append(
            {
                "post_id": f"P{index}",
                "original_text": f"o{index}",
                "mirror_text": f"m{index}",
                "label": index % 2,
                "majority_decision": "remove" if index % 2 else "keep",
                "n_raters": 3,
                "n_keep": 2,
                "n_remove": 1,
                "remove_share": 0.33,
                "is_unanimous": False,
                "sampled_stance": stances[index % len(stances)],
                "sample_toxicity_type": toxicities[index % len(toxicities)],
                "post_1_role": "original",
                "post_2_role": "mirror",
            }
        )
    return pd.DataFrame(rows)


def _gepa_pool_frame(n_per_class: int = 200) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in (0, 1):
        for index in range(n_per_class):
            rows.append(
                {
                    "post_id": f"L{label}_{index}",
                    "label": label,
                    "split": "gepa_pool",
                    "sampled_stance": "left",
                    "sample_toxicity_type": "low",
                    "gepa_subset": "none",
                }
            )
    return pd.DataFrame(rows)


class TestAssignSplits:
    """Tests for assign_splits."""

    def test_stratified_test_and_dev_fractions(self) -> None:
        """Test is 20% and dev is 10% of the original cohort within rounding tolerance."""
        cohort = _synthetic_cohort(100)
        result = assign_splits(cohort, seed=SPLIT_SEED)
        test_count = int((result["split"] == "test").sum())
        dev_count = int((result["split"] == "dev").sum())
        pool_count = int((result["split"] == "gepa_pool").sum())
        assert abs(test_count - 20) <= 1
        assert abs(dev_count - 10) <= 1
        assert test_count + dev_count + pool_count == 100


class TestSampleGepaSubsets:
    """Tests for sample_gepa_subsets."""

    def test_balanced_val_and_train_caps_with_disjoint_ids(self) -> None:
        """Val and train subsets are balanced, capped, and disjoint."""
        pool = _gepa_pool_frame(200)
        result = sample_gepa_subsets(pool, seed=SPLIT_SEED)
        val = result.loc[result["gepa_subset"] == "val"]
        train = result.loc[result["gepa_subset"] == "train"]
        assert len(val) == 300
        assert int((val["label"] == 0).sum()) == 150
        assert int((val["label"] == 1).sum()) == 150
        assert len(train) == 100
        assert int((train["label"] == 0).sum()) == 50
        assert int((train["label"] == 1).sum()) == 50
        assert set(val["post_id"]).isdisjoint(set(train["post_id"]))


class TestComputeSplitHash:
    """Tests for compute_split_hash."""

    def test_hash_is_deterministic(self) -> None:
        """The same cohort frame yields the same split hash."""
        cohort = assign_splits(_synthetic_cohort(100), seed=SPLIT_SEED)
        cohort = sample_gepa_subsets(cohort, seed=SPLIT_SEED)
        first = compute_split_hash(cohort)
        second = compute_split_hash(cohort)
        assert first == second
