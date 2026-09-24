"""Tests for the discovery feature generation CLI."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pandas as pd
import pytest

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src import constants
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.batching import form_mixed_batches
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features import (
    APPROVAL_PATH,
    build_mixed_discovery_row,
    build_single_class_discovery_row,
    main,
)
from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.schemas import (
    BatchFeatureGeneration,
    ExtractedFeature,
    FeatureCategory,
    SingleClassBatchFeatureGeneration,
)


def _sample_cohort() -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for index in range(10):
        rows.append(
            {
                "post_id": f"keep_{index}",
                "original_text": f"keep original {index}",
                "mirror_text": f"keep mirror {index}",
                "modal_decision": constants.DECISION_KEEP,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    for index in range(10):
        rows.append(
            {
                "post_id": f"remove_{index}",
                "original_text": f"remove original {index}",
                "mirror_text": f"remove mirror {index}",
                "modal_decision": constants.DECISION_REMOVE,
                "split": constants.DISCOVERY_SPLIT,
            }
        )
    return pd.DataFrame(rows)


def _mixed_result() -> BatchFeatureGeneration:
    feature = ExtractedFeature(
        message_id="keep_0",
        feature_name="informal_register",
        feature_value="informal",
        category=FeatureCategory.SURFACE_LEXICAL,
        is_open_ended=False,
        evidence_span="quoted",
        rationale="because",
    )
    return BatchFeatureGeneration(batch_index=0, keep_features=[feature], remove_features=[])


def _single_class_result() -> SingleClassBatchFeatureGeneration:
    feature = ExtractedFeature(
        message_id="keep_0",
        feature_name="informal_register",
        feature_value="informal",
        category=FeatureCategory.SURFACE_LEXICAL,
        is_open_ended=False,
        evidence_span="quoted",
        rationale="because",
    )
    return SingleClassBatchFeatureGeneration(batch_index=0, features=[feature])


def test_smoke_runs_one_batch(capsys: pytest.CaptureFixture[str]) -> None:
    """Smoke mode runs exactly one mixed batch LLM call."""
    cohort = _sample_cohort()
    call_count = {"n": 0}

    def _complete(*args, **kwargs):
        call_count["n"] += 1
        return _mixed_result()

    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.load_discovery_cohort",
        return_value=cohort,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.complete_structured",
        side_effect=_complete,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.make_run_timestamp",
        return_value="2026-09-24T12-00-00",
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "--arm",
                    "original_only",
                    "--batch-design",
                    "mixed",
                    "--smoke",
                    "--seed",
                    "42",
                ]
            )
        assert exc_info.value.code == 0
    assert call_count["n"] == 1
    output = capsys.readouterr().out
    assert "batch_design=mixed" in output


def test_production_requires_approval() -> None:
    """Production exits when the approval marker is missing."""
    if APPROVAL_PATH.is_file():
        APPROVAL_PATH.unlink()
    with pytest.raises(SystemExit) as exc_info:
        main(
            [
                "--arm",
                "original_only",
                "--batch-design",
                "mixed",
                "--production",
                "--seed",
                "42",
            ]
        )
    assert exc_info.value.code != 0
    assert "approval_step3_production.json" in str(exc_info.value)


def test_production_runs_when_approved(tmp_path: Path) -> None:
    """Production runs one LLM call per mixed batch when approved."""
    cohort = _sample_cohort()
    batches = form_mixed_batches(cohort)
    call_count = {"n": 0}

    def _complete(*args, **kwargs):
        call_count["n"] += 1
        return _mixed_result()

    approval_path = tmp_path / "approval_step3_production.json"
    approval_path.write_text(
        json.dumps({"approved": True, "approved_at": "2026-09-24T00:00:00", "note": "test"}),
        encoding="utf-8",
    )
    with patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.APPROVAL_PATH",
        approval_path,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.load_discovery_cohort",
        return_value=cohort,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.complete_structured",
        side_effect=_complete,
    ), patch(
        "experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.generate_features.make_run_timestamp",
        return_value="2026-09-24T12-00-00",
    ):
        with pytest.raises(SystemExit) as exc_info:
            main(
                [
                    "--arm",
                    "original_only",
                    "--batch-design",
                    "mixed",
                    "--production",
                    "--seed",
                    "42",
                ]
            )
        assert exc_info.value.code == 0
    assert call_count["n"] == len(batches)


def test_writer_row_shape_mixed() -> None:
    """Mixed discovery rows include the required top-level keys."""
    batch = {
        "batch_id": 0,
        "arm": "original_only",
        "batch_design": constants.BATCH_DESIGN_MIXED,
        "message_ids": ["p1", "p2"],
    }
    row = build_mixed_discovery_row(batch, _mixed_result())
    assert set(row) == {
        "batch_id",
        "arm",
        "batch_design",
        "message_ids",
        "keep_feature_count",
        "remove_feature_count",
        "result",
    }


def test_writer_row_shape_single_class() -> None:
    """Single-class discovery rows include label_class and feature_count."""
    batch = {
        "batch_id": 0,
        "arm": "original_only",
        "batch_design": constants.BATCH_DESIGN_SINGLE_CLASS,
        "message_ids": ["p1"],
        "label_class": constants.DECISION_KEEP,
    }
    row = build_single_class_discovery_row(batch, _single_class_result())
    assert "label_class" in row
    assert "feature_count" in row
    assert "result" in row
