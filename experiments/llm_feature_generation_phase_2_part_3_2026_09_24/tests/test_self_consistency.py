"""Tests for self-consistency Batch re-labeling."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency import (
    run_self_consistency,
    sample_label_pairs,
    score_self_consistency,
)


def _matrix_frame(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": [f"p{i}" for i in range(n)],
            "text_surface": ["original" if i % 2 == 0 else "mirror" for i in range(n)],
            "split": ["discovery"] * n,
            "modal_decision": ["keep"] * n,
            "cb_001": [1] * n,
        }
    )


class TestSampleLabelPairs:
    """Tests for sample_label_pairs."""

    def test_self_consistency_sample_size_200_seed_42(self) -> None:
        matrix = _matrix_frame(500)
        first = sample_label_pairs(matrix, 200, 42)
        second = sample_label_pairs(matrix, 200, 42)
        assert len(first) == 200
        assert first["post_id"].tolist() == second["post_id"].tolist()


class TestScoreSelfConsistency:
    """Tests for score_self_consistency."""

    def test_flags_features_below_threshold(self) -> None:
        baseline = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "text_surface": ["original", "original"],
                "cb_001": [1, 1],
                "cb_002": [1, 0],
            }
        )
        relabeled = pd.DataFrame(
            {
                "post_id": ["p1", "p2"],
                "text_surface": ["original", "original"],
                "cb_001": [1, 1],
                "cb_002": [0, 0],
            }
        )
        scores = score_self_consistency(baseline, relabeled, ["cb_001", "cb_002"])
        assert "cb_002" in scores["features_below_threshold"]


class TestRunSelfConsistency:
    """Tests for run_self_consistency."""

    def test_self_consistency_uses_batch_api(self, tmp_path: Path) -> None:
        codebook = tmp_path / "approved" / "codebook.json"
        codebook.parent.mkdir(parents=True)
        codebook.write_text(
            json.dumps({"version": "v1", "features": [{"feature_id": "cb_001", "name": "n", "definition": "d"}]}),
            encoding="utf-8",
        )
        (codebook.parent / constants.APPROVAL_JSON_FILENAME).write_text("{}", encoding="utf-8")
        matrix_path = tmp_path / "matrix.parquet"
        _matrix_frame(300).to_parquet(matrix_path, index=False)
        mock_submit = MagicMock(return_value="batch_1")
        mock_poll = MagicMock(return_value=MagicMock(status="completed"))
        mock_download = MagicMock(return_value=([], []))
        mock_parse = MagicMock(return_value=[])
        with (
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency.paths.self_consistency_dir",
                return_value=tmp_path / "sc",
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency.load_union_cohort",
                return_value=pd.DataFrame(
                    {
                        "post_id": [f"p{i}" for i in range(300)],
                        "original_text": ["t"] * 300,
                        "mirror_text": ["m"] * 300,
                        "split": ["discovery"] * 300,
                        "modal_decision": ["keep"] * 300,
                    }
                ),
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.submit_batch",
                mock_submit,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.poll_batch",
                mock_poll,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.download_results",
                mock_download,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.parse_batch_output",
                mock_parse,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.append_batch_cost_log",
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.self_consistency.score_self_consistency",
                return_value={
                    "per_feature": {"cb_001": {"agreement_rate": 0.95, "n_pairs": 200}},
                    "features_below_threshold": [],
                },
            ),
        ):
            run_self_consistency(codebook, matrix_path, 200, 42, client=MagicMock())
        assert mock_submit.call_count == 1
