"""Tests for HDBSCAN/K-Means clustering and seed stability."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import cluster_embeddings as ce
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants


def test_hdbscan_returns_labels() -> None:
    matrix = np.random.default_rng(0).random((20, 256))
    labels = ce.run_hdbscan(matrix, 5, 42)
    assert len(labels) == 20


def test_kmeans_sweep_writes_k_selection() -> None:
    matrix = np.random.default_rng(1).random((30, 256))
    k_selection, _labels = ce.run_kmeans_sweep(matrix, 2, 10, 42)
    assert "rows" in k_selection
    assert k_selection["rows"]
    first = k_selection["rows"][0]
    assert "silhouette" in first or "inertia" in first


class TestRunKmeansSweepWide:
    """Tests for run_kmeans_sweep_wide."""

    def test_returns_selected_k_and_edge_flags(self) -> None:
        matrix = np.random.default_rng(2).random((120, 256))
        result = ce.run_kmeans_sweep_wide(matrix, 42)
        expected_keys = {"selected_k", "rows", "hits_k_min_edge", "hits_k_max_edge"}
        assert expected_keys.issubset(result.keys())
        assert constants.KMEANS_WIDE_K_MIN <= result["selected_k"] <= constants.KMEANS_WIDE_K_MAX


class TestComputeKmeansStabilityAtK:
    """Tests for compute_kmeans_stability_at_k."""

    def test_returns_pairwise_ari_keys(self) -> None:
        matrix = np.random.default_rng(3).random((40, 256))
        feature_ids = [f"f{i}" for i in range(40)]
        payload = ce.compute_kmeans_stability_at_k(matrix, feature_ids, selected_k=4)
        assert set(payload["adjusted_rand_index"]) == {"42_43", "42_44", "43_44"}
        assert -1.0 <= payload["mean_ari"] <= 1.0


class TestComputeHdbscanSubsampleStability:
    """Tests for compute_hdbscan_subsample_stability."""

    def test_returns_summary_stats(self) -> None:
        matrix = np.random.default_rng(4).random((50, 256))
        reference_labels = np.array([0] * 25 + [1] * 25)
        result = ce.compute_hdbscan_subsample_stability(matrix, reference_labels, 5)
        assert result["repeats"] == constants.HDBSCAN_SUBSAMPLE_REPEATS
        assert "mean" in result["ari_all_points"]


def test_assignments_json_maps_feature_ids() -> None:
    labels = np.array([0, 1, 0])
    feature_ids = ["a", "b", "c"]
    mapping = ce.assignments_to_json(labels, feature_ids)
    assert set(mapping.keys()) == set(feature_ids)


def test_seed_pair_ari_identical_assignments() -> None:
    assignments = {"f1": 0, "f2": 1, "f3": 0}
    score = ce.compute_seed_pair_ari(assignments, dict(assignments))
    assert score == 1.0


def test_seed_pair_ari_random_assignments() -> None:
    ids = [f"f{i}" for i in range(50)]
    a = {feature_id: i % 5 for i, feature_id in enumerate(ids)}
    b = {feature_id: (i * 7) % 11 for i, feature_id in enumerate(ids)}
    score = ce.compute_seed_pair_ari(a, b)
    assert -0.2 <= score <= 0.2


def test_stability_within_arm_json_schema(tmp_path: Path) -> None:
    embed_dir = tmp_path / "embed"
    embed_dir.mkdir()
    for seed in (42, 43, 44):
        seed_dir = embed_dir / f"clusters_seed_{seed}"
        seed_dir.mkdir()
        assignments = {f"f{i}": i % 3 for i in range(10)}
        (seed_dir / "assignments_hdbscan.json").write_text(
            json.dumps(assignments),
            encoding="utf-8",
        )
    payload = ce.aggregate_stability_within_arm(embed_dir, "original_only")
    assert "adjusted_rand_index" in payload
    for key in ("42_43", "42_44", "43_44"):
        assert key in payload["adjusted_rand_index"]


def test_write_stability_v2_artifacts(tmp_path: Path) -> None:
    embed_dir = tmp_path / "embed"
    embed_dir.mkdir()
    n_rows = 60
    matrix = np.random.default_rng(5).random((n_rows, constants.EMBEDDING_DIM)).astype(np.float32)
    np.save(embed_dir / "embeddings.npy", matrix)
    records = [
        {
            "feature_id": f"f{i}",
            "text_embedded": f"feature {i}",
        }
        for i in range(n_rows)
    ]
    jsonl_lines = "\n".join(json.dumps(record) for record in records)
    (embed_dir / "features.jsonl").write_text(jsonl_lines + "\n", encoding="utf-8")
    for seed in constants.CLUSTER_SEEDS:
        seed_dir = embed_dir / f"clusters_seed_{seed}"
        seed_dir.mkdir()
        labels = np.array([i % 4 for i in range(n_rows)])
        assignments = ce.assignments_to_json(labels, [r["feature_id"] for r in records])
        (seed_dir / "assignments_hdbscan.json").write_text(
            json.dumps(assignments),
            encoding="utf-8",
        )
        (seed_dir / "metadata.json").write_text(
            json.dumps({"min_cluster_size": 5}),
            encoding="utf-8",
        )
    stability_path, wide_path = ce.write_stability_v2_artifacts(embed_dir, "original_only")
    assert stability_path.name == constants.STABILITY_V2_FILENAME
    assert wide_path.name == constants.K_SELECTION_WIDE_FILENAME
    payload = json.loads(stability_path.read_text(encoding="utf-8"))
    assert "kmeans_seed_stability" in payload
    assert "hdbscan_subsample_stability" in payload
