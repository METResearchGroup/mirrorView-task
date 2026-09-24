"""Tests for HDBSCAN/K-Means clustering and seed stability."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import cluster_embeddings as ce


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
