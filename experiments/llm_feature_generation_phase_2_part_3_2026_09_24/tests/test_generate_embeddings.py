"""Tests for discovery flattening and Titan embedding helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import generate_embeddings as ge
from shared.embeddings.bedrock import EMBEDDING_DIMENSIONS


def _mixed_discovery_row() -> dict:
    return {
        "batch_id": 0,
        "arm": "original_only",
        "batch_design": "mixed",
        "message_ids": ["m1"],
        "result": {
            "keep_features": [
                {
                    "message_id": "m1",
                    "feature_name": "keep_a",
                    "feature_value": "v1",
                    "category": "topic_subject",
                    "rationale": "r1",
                    "evidence_span": "e1",
                },
                {
                    "message_id": "m2",
                    "feature_name": "keep_b",
                    "feature_value": "v2",
                    "category": "topic_subject",
                    "rationale": "r2",
                    "evidence_span": "e2",
                },
            ],
            "remove_features": [
                {
                    "message_id": "m3",
                    "feature_name": "remove_a",
                    "feature_value": "v3",
                    "category": "pragmatics_intent",
                    "rationale": "r3",
                    "evidence_span": "e3",
                },
            ],
        },
    }


def test_flatten_mixed_discovery_row() -> None:
    records = ge.flatten_discovery_to_features([_mixed_discovery_row()])
    assert len(records) == 3
    for record in records:
        assert record["feature_id"]
        assert record["text_embedded"]


def test_build_feature_embed_text_format() -> None:
    feature = {
        "feature_name": "name",
        "feature_value": "value",
        "rationale": "because",
    }
    assert ge.build_feature_embed_text(feature) == "name: value. because"


@patch("experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_embeddings.create_embedding")
def test_embed_features_shape(mock_create) -> None:
    mock_create.return_value = {
        "embedding": [0.1] * EMBEDDING_DIMENSIONS,
        "dimensions": EMBEDDING_DIMENSIONS,
    }
    records = [{"text_embedded": "x"} for _ in range(5)]
    matrix = ge.embed_features(records)
    assert matrix.shape == (5, EMBEDDING_DIMENSIONS)


def test_write_embedding_artifacts_files(tmp_path: Path) -> None:
    records = [
        {
            "feature_id": "mixed_0_keep_0",
            "batch_id": 0,
            "message_id": "m",
            "feature_name": "n",
            "feature_value": "v",
            "category": "c",
            "rationale": "r",
            "evidence_span": None,
            "text_embedded": "n: v. r",
        }
    ]
    matrix = np.zeros((1, EMBEDDING_DIMENSIONS), dtype=np.float32)
    ge.write_embedding_artifacts(tmp_path, records, matrix, {"arm": "original_only"})
    assert (tmp_path / "features.jsonl").is_file()
    assert (tmp_path / "embeddings.npy").is_file()
    assert (tmp_path / "feature_ids.json").is_file()
    assert (tmp_path / "metadata.json").is_file()


def test_feature_ids_align_with_matrix(tmp_path: Path) -> None:
    records = [
        {
            "feature_id": "mixed_0_keep_0",
            "batch_id": 0,
            "message_id": "m",
            "feature_name": "n",
            "feature_value": "v",
            "category": "c",
            "rationale": "r",
            "evidence_span": None,
            "text_embedded": "n: v. r",
        }
    ]
    matrix = np.zeros((1, EMBEDDING_DIMENSIONS), dtype=np.float32)
    ge.write_embedding_artifacts(tmp_path, records, matrix, {"arm": "original_only"})
    feature_ids = json.loads((tmp_path / "feature_ids.json").read_text(encoding="utf-8"))
    loaded = np.load(tmp_path / "embeddings.npy")
    assert len(feature_ids) == loaded.shape[0]
