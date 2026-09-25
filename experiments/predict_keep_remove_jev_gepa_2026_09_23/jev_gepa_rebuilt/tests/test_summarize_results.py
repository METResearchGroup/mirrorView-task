"""Tests for rebuilt GEPA results summarizer."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    ACCEPTANCE_LOG_FILENAME,
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_RUN_DIRNAME,
    REFLECTION_USAGE_JSONL,
    STOP_REASON_FILENAME,
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate import (
    TEST_RESULTS_FILENAME,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.summarize_results import (
    STAGE_A_UNION_A1_BASELINE_TEST_F1,
    _upsert_results_section,
    collect_ablation_summaries,
    format_rebuilt_gepa_section,
    format_results_markdown_table,
    load_ablation_summary,
)


def _write_r1_fixture(ablation_dir: Path) -> None:
    gepa_run = ablation_dir / GEPA_RUN_DIRNAME
    gepa_run.mkdir(parents=True, exist_ok=True)
    study_instruction = "Keep civil discourse; remove harassment."
    (ablation_dir / DEV_SELECTION_FILENAME).write_text(
        json.dumps(
            {
                "selected_candidate_idx": 1,
                "threshold": 0.42,
                "dev_a_f1": 0.61,
                "dev_b_f1": 0.58,
                "reflection_total_usd": 1.25,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (gepa_run / GEPA_RESULT_FILENAME).write_text(
        json.dumps(
            {
                "candidates": [
                    {STUDY_COMPONENT_KEY: "seed"},
                    {STUDY_COMPONENT_KEY: study_instruction},
                    {STUDY_COMPONENT_KEY: "alt"},
                ],
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (gepa_run / STOP_REASON_FILENAME).write_text(
        json.dumps({"stop_reason": "max_metric_calls", "reflection_cost_usd": 1.25})
        + "\n",
        encoding="utf-8",
    )
    (gepa_run / ACCEPTANCE_LOG_FILENAME).write_text(
        "\n".join(
            [
                json.dumps({"candidate_idx": 1, "accepted": True}),
                json.dumps({"candidate_idx": 2, "accepted": False}),
                json.dumps({"candidate_idx": 3, "accepted": True}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (gepa_run / REFLECTION_USAGE_JSONL).write_text(
        "\n".join(
            [
                json.dumps({"usd": 0.5}),
                json.dumps({"usd": 0.75}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    (ablation_dir / TEST_RESULTS_FILENAME).write_text(
        json.dumps(
            {
                "metrics_at_dev_threshold": {"f1": 0.5521},
                "metrics_at_0_5": {"f1": 0.5410},
            }
        )
        + "\n",
        encoding="utf-8",
    )


class TestSummarizeResults:
    """Tests for load_ablation_summary and format_results_markdown_table."""

    def test_load_ablation_summary_reads_fixture_metrics(self, tmp_path: Path) -> None:
        """Fixture artifacts yield test F1 and positive reflection USD."""
        ablation_dir = tmp_path / "R1_gepa_pair"
        _write_r1_fixture(ablation_dir)

        result = load_ablation_summary("R1_gepa_pair", tmp_path)

        assert result["ablation_id"] == "R1_gepa_pair"
        assert result["test_f1"] == 0.5521
        assert result["test_f1_at_0_5"] == 0.5410
        assert result["dev_a_f1"] == 0.61
        assert result["dev_b_f1"] == 0.58
        assert result["reflection_usd"] > 0
        assert result["iterations"] == 2
        assert result["accept_rate"] == 2 / 3
        assert result["stop_reason"] == "max_metric_calls"
        assert result["prompt_chars"] == len("Keep civil discourse; remove harassment.")

    def test_format_results_markdown_table_includes_baseline(self) -> None:
        """Markdown table cites R1 row and union A1 baseline F1."""
        rows = [
            {
                "ablation_id": "R1_gepa_pair",
                "dev_a_f1": 0.61,
                "dev_b_f1": 0.58,
                "test_f1": 0.5521,
                "test_f1_at_0_5": 0.5410,
                "iterations": 2,
                "accept_rate": 2 / 3,
                "stop_reason": "max_metric_calls",
                "reflection_usd": 1.25,
                "prompt_chars": 40,
            }
        ]
        markdown = format_results_markdown_table(
            rows,
            baseline_a1_test_f1=STAGE_A_UNION_A1_BASELINE_TEST_F1,
        )

        assert "R1_gepa_pair" in markdown
        assert "0.538" in markdown
        assert "A1_pair_study_prompt" in markdown

    def test_collect_ablation_summaries_skips_missing_dirs(self, tmp_path: Path) -> None:
        """Ablation IDs without output directories are omitted."""
        ablation_dir = tmp_path / "R1_gepa_pair"
        _write_r1_fixture(ablation_dir)

        summaries = collect_ablation_summaries(
            ["R1_gepa_pair", "R2_majority_weighted", "R9_missing"],
            tmp_path,
        )

        assert [row["ablation_id"] for row in summaries] == ["R1_gepa_pair"]

    def test_upsert_replaces_blocked_section(self, tmp_path: Path) -> None:
        """The credit-stop section is replaced by the scored rebuilt section."""
        results_path = tmp_path / "RESULTS.md"
        results_path.write_text(
            "# Results\n\n## Stage A\n\nKept.\n\n"
            "## Rebuilt GEPA on the union cohort (blocked)\n\n"
            "Old credit stop table.\n",
            encoding="utf-8",
        )
        section = format_rebuilt_gepa_section(
            [
                {
                    "ablation_id": "R1_gepa_pair",
                    "dev_a_f1": 0.61,
                    "dev_b_f1": 0.58,
                    "test_f1": 0.5521,
                    "test_f1_at_0_5": 0.5410,
                    "iterations": 2,
                    "accept_rate": 2 / 3,
                    "stop_reason": "max_metric_calls",
                    "reflection_usd": 1.25,
                    "prompt_chars": 40,
                }
            ],
            STAGE_A_UNION_A1_BASELINE_TEST_F1,
        )

        _upsert_results_section(results_path, section)

        text = results_path.read_text(encoding="utf-8")
        assert "## Rebuilt GEPA on the union cohort (blocked)" not in text
        assert "## Rebuilt GEPA (jev_gepa_rebuilt)" in text
        assert "Old credit stop table." not in text
        assert "## Stage A" in text
