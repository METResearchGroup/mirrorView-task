"""Tests for nested union split preservation and GEPA top-up."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.splits import (
    SPLIT_SEED,
    assign_nested_splits,
    retain_and_top_up_gepa_subsets,
)


def _cohort_row(
    post_id: str,
    label: int,
    stance: str = "left",
    toxicity: str = "low",
) -> dict[str, object]:
    return {
        "post_id": post_id,
        "original_text": "o",
        "mirror_text": "m",
        "label": label,
        "majority_decision": "remove" if label else "keep",
        "n_raters": 3,
        "n_keep": 2 if label == 0 else 1,
        "n_remove": 1 if label == 0 else 2,
        "remove_share": 0.33,
        "is_unanimous": False,
        "sampled_stance": stance,
        "sample_toxicity_type": toxicity,
        "post_1_role": "original",
        "post_2_role": "mirror",
        "n_raters_part2": 0,
        "n_raters_part3": 3,
        "in_part3_cohort_a": True,
        "label_changed_vs_part3": False,
    }


class TestAssignNestedSplits:
    """Tests for assign_nested_splits."""

    def test_preserves_split_for_overlapping_posts(self) -> None:
        """Posts present in the frozen split file keep their original split."""
        frozen = pd.DataFrame(
            [
                {**_cohort_row("P1", 0), "split": "test", "gepa_subset": "none"},
                {**_cohort_row("P2", 1), "split": "dev", "gepa_subset": "none"},
            ]
        )
        union = pd.DataFrame(
            [
                _cohort_row("P1", 0),
                _cohort_row("P2", 1),
                _cohort_row("P3", 0),
            ]
        )
        result = assign_nested_splits(union, frozen, seed=SPLIT_SEED)
        assert result.loc[result["post_id"] == "P1", "split"].iloc[0] == "test"
        assert result.loc[result["post_id"] == "P2", "split"].iloc[0] == "dev"
        assert result.loc[result["post_id"] == "P3", "split"].notna().all()


class TestRetainAndTopUpGepaSubsets:
    """Tests for retain_and_top_up_gepa_subsets."""

    def test_replaces_dropped_val_member_and_keeps_balanced_caps(self) -> None:
        """A frozen val member that drops out is replaced from the pool."""
        frozen_rows: list[dict[str, object]] = []
        for index in range(150):
            frozen_rows.append(
                {
                    **_cohort_row(f"K{index}", 0),
                    "split": "gepa_pool",
                    "gepa_subset": "val",
                }
            )
        for index in range(150):
            frozen_rows.append(
                {
                    **_cohort_row(f"R{index}", 1),
                    "split": "gepa_pool",
                    "gepa_subset": "val",
                }
            )
        frozen = pd.DataFrame(frozen_rows)
        union = frozen.drop(index=0).copy()
        replacement = _cohort_row("NEW0", 0)
        replacement["split"] = "gepa_pool"
        union = pd.concat([union, pd.DataFrame([replacement])], ignore_index=True)
        result, report = retain_and_top_up_gepa_subsets(union, frozen, seed=SPLIT_SEED)
        val = result.loc[result["gepa_subset"] == "val"]
        assert len(val) == 300
        assert int((val["label"] == 0).sum()) == 150
        assert int((val["label"] == 1).sum()) == 150
        assert "K0" not in set(val["post_id"])
        assert report.val_members_changed >= 1
