"""Tests for ablation metrics that do not fit BERTopic."""

from __future__ import annotations

import numpy as np
import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a0_baselines import run_kmeans_sweep
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.a4_design import run_a4_design_comparison
from experiments.bertopic_original_mirror_part3_2026_09_24.src.ablations.summary import (
    pairwise_ari_hungarian,
    spearman_q5_keep_rate,
)


class TestKMeansSweep:
    """Tests for run_kmeans_sweep."""

    def test_kmeans_sweep_records_all_k(self) -> None:
        """Every requested k gets a silhouette score, and the sweep repeats."""
        rng = np.random.default_rng(0)
        embeddings = rng.normal(size=(40, 8))
        doc_ids = [f"d{index}" for index in range(40)]

        first = run_kmeans_sweep(embeddings, doc_ids, k_min=2, k_max=5, seed=42)
        second = run_kmeans_sweep(embeddings, doc_ids, k_min=2, k_max=5, seed=42)

        assert len(first) == 4
        assert first["silhouette_score"].map(lambda value: isinstance(value, float)).all()
        assert first["silhouette_score"].tolist() == second["silhouette_score"].tolist()


class TestPairwiseAri:
    """Tests for pairwise_ari_hungarian."""

    def test_hungarian_pairwise_ari_identical_clusterings(self) -> None:
        """A label permutation of the same clustering has ARI 1."""
        result = pairwise_ari_hungarian([0, 0, 1, 1], [1, 1, 0, 0])

        assert result == 1.0


class TestSpearmanKeepRate:
    """Tests for spearman_q5_keep_rate."""

    def test_spearman_q5_rank_unchanged(self) -> None:
        """Identical keep-rate sequences correlate at 1."""
        rho = spearman_q5_keep_rate([0.9, 0.5, 0.1], [0.9, 0.5, 0.1])

        assert rho == 1.0


class TestA4DesignComparison:
    """Tests for run_a4_design_comparison."""

    def test_a4_reads_production_paths_without_writing_topics(self, tmp_path) -> None:
        """Design comparison writes metrics beside the given runs."""
        original = _write_assignments(tmp_path / "topics" / "original", "original", ["a", "b"], [0, 1])
        mirror = _write_assignments(tmp_path / "topics" / "mirror", "mirror", ["a", "b"], [0, 1])
        joint = tmp_path / "topics" / "joint"
        joint.mkdir(parents=True)
        pd.DataFrame(
            {
                "post_id": ["a", "a", "b", "b"],
                "text_role": ["original", "mirror", "original", "mirror"],
                "topic": [0, 0, 1, 1],
            }
        ).to_parquet(joint / "assignments.parquet", index=False)
        assigned = tmp_path / "assignments"
        assigned.mkdir()
        pd.DataFrame(
            {"post_id": ["a", "b"], "original_topic": [0, 1], "mirror_topic": [0, 1]}
        ).to_parquet(assigned / "pair_assignments.parquet", index=False)

        run_a4_design_comparison(original, mirror, joint, assigned, tmp_path / "a4")

        assert (tmp_path / "a4" / "separate" / "q2_q3_metrics.json").exists()
        assert not (tmp_path / "outputs" / "topics").exists()


def _write_assignments(path, role: str, post_ids: list[str], topics: list[int]):
    path.mkdir(parents=True)
    pd.DataFrame({"post_id": post_ids, "text_role": role, "topic": topics}).to_parquet(
        path / "assignments.parquet",
        index=False,
    )
    return path
