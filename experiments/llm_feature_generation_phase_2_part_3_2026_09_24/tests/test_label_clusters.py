"""Tests for HDBSCAN cluster labeling."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import label_clusters as lc
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import ClusterLabelResult


def _feature_records() -> list[dict]:
    return [
        {
            "feature_id": f"f{i}",
            "message_id": f"m{i}",
            "feature_name": "n",
            "feature_value": "v",
            "category": "c",
            "rationale": "r",
            "label_class": "keep",
        }
        for i in range(25)
    ]


def test_skips_noise_cluster() -> None:
    assignments = {"f0": -1, "f1": 0, "f2": 0}
    items = lc.build_cluster_label_items(
        assignments,
        _feature_records()[:3],
        8,
        42,
    )
    assert all(item["cluster_id"] != -1 for item in items)


def test_sample_per_cluster_cap() -> None:
    assignments = {f"f{i}": 0 for i in range(20)}
    records = _feature_records()[:20]
    items = lc.build_cluster_label_items(assignments, records, 8, 42)
    assert len(items[0]["sampled_features"]) <= 8


@patch("experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_clusters.llm_client.complete_structured")
def test_label_clusters_writes_one_file_per_cluster(mock_complete, tmp_path: Path) -> None:
    parsed_results = [
        ClusterLabelResult(cluster_id=0, cluster_label="a", definition="d", salience_notes=""),
        ClusterLabelResult(cluster_id=1, cluster_label="b", definition="d", salience_notes=""),
        ClusterLabelResult(cluster_id=2, cluster_label="c", definition="d", salience_notes=""),
    ]

    def complete_side_effect(messages, response_model, **kwargs):
        index = kwargs["call_index"]
        output_dir = kwargs["output_dir"]
        artifact = output_dir / f"{index:05d}_2026-01-01T00-00-00.json"
        artifact.write_text(json.dumps({"request": {}, "response": {}, "usage": {}}), encoding="utf-8")
        return parsed_results[index]

    mock_complete.side_effect = complete_side_effect

    items = [
        {
            "cluster_id": i,
            "label_class": "keep",
            "n_members": 3,
            "sampled_features": [{"feature_id": f"f{i}", "message_id": "m", "feature_name": "n", "feature_value": "v", "category": "c", "rationale": "r", "evidence_span": None}],
        }
        for i in range(3)
    ]
    lc.label_clusters_for_run(items, "original_only", 42, tmp_path)
    assert len(list(tmp_path.glob("[0-9]*_*.json"))) == 3


@patch("experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_clusters.llm_client.complete_structured")
def test_cluster_label_row_shape(mock_complete, tmp_path: Path) -> None:
    result = ClusterLabelResult(
        cluster_id=0,
        cluster_label="topic",
        definition="def",
        salience_notes="",
    )

    def complete_side_effect(messages, response_model, **kwargs):
        artifact = tmp_path / "00000_2026-01-01T00-00-00.json"
        artifact.write_text(json.dumps({"request": {}, "response": {}, "usage": {}}), encoding="utf-8")
        return result

    mock_complete.side_effect = complete_side_effect
    items = [
        {
            "cluster_id": 0,
            "label_class": "keep",
            "n_members": 2,
            "sampled_features": [
                {
                    "feature_id": "f0",
                    "message_id": "m",
                    "feature_name": "n",
                    "feature_value": "v",
                    "category": "c",
                    "rationale": "r",
                    "evidence_span": None,
                }
            ],
        }
    ]
    lc.label_clusters_for_run(items, "original_only", 42, tmp_path)
    payload = json.loads(next(tmp_path.glob("[0-9]*_*.json")).read_text(encoding="utf-8"))
    row = payload["cluster_label_row"]
    assert row["cluster_id"] == 0
    assert row["arm"] == "original_only"
    assert row["seed"] == 42
    assert row["result"]["cluster_label"] == "topic"
