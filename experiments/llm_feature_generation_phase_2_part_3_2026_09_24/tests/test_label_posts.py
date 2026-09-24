"""Tests for post labeling CLI and helpers."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import batch_client, constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts import (
    ApprovalRequiredError,
    assemble_label_matrix,
    main,
    require_approved_codebook,
    run_production,
    run_smoke,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.prompts import build_labeling_prompt
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import PostLabelResult


def _write_codebook(path: Path, approved: bool) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"version": "v1", "features": [{"feature_id": "cb_001", "name": "n", "definition": "d"}]}),
        encoding="utf-8",
    )
    if approved:
        (path.parent / constants.APPROVAL_JSON_FILENAME).write_text(
            json.dumps({"approved_by": "t"}),
            encoding="utf-8",
        )
    return path


def _cohort_frame(n: int) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "post_id": [f"p{i}" for i in range(n)],
            "original_text": [f"o{i}" for i in range(n)],
            "mirror_text": [f"m{i}" for i in range(n)],
            "split": ["discovery"] * n,
            "modal_decision": ["keep"] * n,
        }
    )


class TestRequireApprovedCodebook:
    """Tests for require_approved_codebook."""

    def test_label_posts_requires_approval_marker(self, tmp_path: Path) -> None:
        codebook = _write_codebook(tmp_path / "draft_x" / "codebook.json", approved=False)
        with pytest.raises(ApprovalRequiredError):
            require_approved_codebook(codebook)


class TestBuildLabelingPrompt:
    """Tests for build_labeling_prompt stability."""

    def test_build_prompt_prefix_stable_across_calls(self) -> None:
        codebook = [{"feature_id": "cb_001", "name": "a", "definition": "b"}]
        first = build_labeling_prompt(codebook, "text one", "original")
        second = build_labeling_prompt(codebook, "text two", "original")
        assert first[0]["content"] == second[0]["content"]
        assert first[1]["content"] != second[1]["content"]


class TestRunSmoke:
    """Tests for run_smoke."""

    def test_smoke_labels_twenty_posts_via_llm_client(self, tmp_path: Path) -> None:
        codebook = _write_codebook(tmp_path / "approved_x" / "codebook.json", approved=True)
        cohort = _cohort_frame(25)
        mock_complete = MagicMock(return_value=PostLabelResult(labels={"cb_001": True}))
        with (
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.load_union_cohort",
                return_value=cohort,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.llm_client.complete_structured",
                mock_complete,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.paths.shared_label_dir",
                return_value=tmp_path,
            ),
        ):
            result = run_smoke(codebook, ("original", "mirror"), limit=20, seed=42)
        assert result["direct_llm_calls"] == 40
        assert mock_complete.call_count == 40


class TestRunProduction:
    """Tests for run_production spend gate and resume."""

    def test_projected_batch_cost_under_cap_before_submit(self, tmp_path: Path) -> None:
        codebook = _write_codebook(tmp_path / "approved_x" / "codebook.json", approved=True)
        with (
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.load_union_cohort",
                return_value=_cohort_frame(2),
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.paths.shared_label_dir",
                return_value=tmp_path / "label",
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.estimate_batch_cost",
                return_value=batch_client.BatchCostEstimate(4, 1, 1, 1.0, 24.99, 25.99),
            ),
        ):
            with pytest.raises(SystemExit):
                run_production(codebook, ("original", "mirror"), client=MagicMock())

    def test_resume_skips_labeled_post_ids(self, tmp_path: Path) -> None:
        codebook = _write_codebook(tmp_path / "approved_x" / "codebook.json", approved=True)
        run_dir = tmp_path / "label" / "2026-01-01T00-00-00"
        run_dir.mkdir(parents=True)
        labels = run_dir / "labels.jsonl"
        labels.write_text(
            json.dumps(
                {
                    "post_id": "p0",
                    "text_surface": "original",
                    "labels": {"cb_001": True},
                    "labeled_at": "t",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        mock_build = MagicMock(return_value=[run_dir / "batch_inputs" / "batch_input_000.jsonl"])
        with (
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.load_union_cohort",
                return_value=_cohort_frame(2),
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts.paths.shared_label_dir",
                return_value=tmp_path / "label",
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts._resolve_production_run_dir",
                return_value=run_dir,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.build_batch_jsonl",
                mock_build,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batch_client.estimate_batch_cost",
                return_value=batch_client.BatchCostEstimate(3, 1, 1, 0.01, 0.0, 0.01),
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts._poll_and_persist_batches",
                return_value=True,
            ),
            patch(
                "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.label_posts._submit_all_batches",
                return_value=[],
            ),
        ):
            run_production(codebook, ("original", "mirror"), client=MagicMock())
        skip_ids = mock_build.call_args.kwargs["skip_custom_ids"]
        assert "p0__original" in skip_ids


class TestAssembleLabelMatrix:
    """Tests for assemble_label_matrix."""

    def test_assemble_label_matrix_wide_format(self, tmp_path: Path) -> None:
        labels_path = tmp_path / "labels.jsonl"
        rows = []
        for post_id in ("p0", "p1"):
            for surface in ("original", "mirror"):
                rows.append(
                    {
                        "post_id": post_id,
                        "text_surface": surface,
                        "labels": {"cb_001": True, "cb_002": False},
                    }
                )
        labels_path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
        cohort = _cohort_frame(2)
        out = tmp_path / "matrix.parquet"
        frame = assemble_label_matrix(labels_path, cohort, ["cb_001", "cb_002"], out)
        assert list(frame.columns) == [
            "post_id",
            "text_surface",
            "split",
            "modal_decision",
            "cb_001",
            "cb_002",
        ]
        assert len(frame) == 4
        assert out.is_file()
