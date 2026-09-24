"""Tests for union cohort Stage A scoring helpers."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_baseline.run import (
    ScoringCounts,
    _build_shared_test_comparison,
    finalize_union_ablation,
    seed_reused_predictions,
    study_part_coverage_label,
)


class TestStudyPartCoverageLabel:
    """Tests for study_part_coverage_label."""

    @pytest.mark.parametrize(
        "part2,part3,expected",
        [
            (5, 0, "part2_only"),
            (0, 8, "part3_only"),
            (3, 4, "both"),
            (0, 0, "unknown"),
        ],
    )
    def test_maps_rater_counts(self, part2: int, part3: int, expected: str) -> None:
        result = study_part_coverage_label(part2, part3)
        assert result == expected


class TestSeedReusedPredictions:
    """Tests for seed_reused_predictions."""

    def test_copies_only_union_post_ids(self, tmp_path: Path) -> None:
        source_dir = tmp_path / "source"
        source_dir.mkdir()
        union_dir = tmp_path / "union"
        union_dir.mkdir()
        source_path = source_dir / "predictions.jsonl"
        source_path.write_text(
            "\n".join(
                [
                    json.dumps({"post_id": "keep-me", "probability_remove": 0.1}),
                    json.dumps({"post_id": "drop-me", "probability_remove": 0.2}),
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        union_ids = {"keep-me", "other-new"}

        seeded, skipped = seed_reused_predictions(
            source_predictions_path=source_path,
            union_predictions_path=union_dir / "predictions.jsonl",
            union_post_ids=union_ids,
        )

        assert seeded == 1
        assert skipped == 1
        lines = (union_dir / "predictions.jsonl").read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 1
        assert json.loads(lines[0])["post_id"] == "keep-me"

    def test_does_not_duplicate_existing_union_rows(self, tmp_path: Path) -> None:
        source_path = tmp_path / "source.jsonl"
        union_path = tmp_path / "union.jsonl"
        source_path.write_text(
            json.dumps({"post_id": "post-a", "probability_remove": 0.5}) + "\n",
            encoding="utf-8",
        )
        union_path.write_text(
            json.dumps({"post_id": "post-a", "probability_remove": 0.5}) + "\n",
            encoding="utf-8",
        )

        seeded, skipped = seed_reused_predictions(
            source_predictions_path=source_path,
            union_predictions_path=union_path,
            union_post_ids={"post-a"},
        )

        assert seeded == 0
        assert skipped == 0
        assert union_path.read_text(encoding="utf-8").count("\n") == 1


class TestSharedTestComparison:
    """Tests for _build_shared_test_comparison."""

    def test_part3_labels_match_reference_metrics(self) -> None:
        labels = pd.DataFrame(
            {
                "post_id": ["shared-test"],
                "split": ["test"],
                "keep_remove_label": [1],
                "p_remove": [0.9],
            }
        )
        part3_cohort = pd.DataFrame(
            {
                "post_id": ["shared-test"],
                "split": ["test"],
                "label": [1],
            }
        )
        reference = {
            "metrics_at_0_5": {
                "test": {
                    "f1": 1.0,
                    "precision": 1.0,
                    "recall": 1.0,
                    "accuracy": 1.0,
                }
            }
        }

        shared = _build_shared_test_comparison(
            labels,
            part3_cohort=part3_cohort,
            part3_reference_results=reference,
            tolerance=1e-4,
        )

        assert shared["n_shared_test_posts"] == 1
        assert shared["metrics_part3_labels"]["f1"] == pytest.approx(1.0)
        assert shared["matches_part3_reference"] is True


class TestFinalizeUnionAblation:
    """Tests for finalize_union_ablation."""

    def test_writes_scoring_counts(self, tmp_path: Path) -> None:
        cohort = pd.read_parquet(
            Path(
                "experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_union_splits.parquet"
            )
        ).head(200)
        part3_cohort = pd.read_parquet(
            Path("experiments/predict_keep_remove_jev_gepa_2026_09_23/data/cohort_a_splits.parquet")
        )
        output_dir = tmp_path / "A1_pair_study_prompt"
        output_dir.mkdir(parents=True)
        with (output_dir / "predictions.jsonl").open("w", encoding="utf-8") as handle:
            for row in cohort.itertuples():
                handle.write(
                    json.dumps({"post_id": str(row.post_id), "probability_remove": 0.5}) + "\n"
                )
        (output_dir / "requests.jsonl").write_text("", encoding="utf-8")

        results = finalize_union_ablation(
            output_dir,
            cohort,
            part3_cohort=part3_cohort,
            part3_reference_results=None,
            scoring_counts=ScoringCounts(posts_reused=10, posts_new_scored=5, requests_new=0),
        )

        assert results["scoring_counts"]["posts_reused"] == 10
        assert results["cohort_source"] == "union"
