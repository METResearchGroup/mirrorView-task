"""Tests for RESULTS.md assembly."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.llm_feature_generation_phase_2_part_3_2026_09_24.src.write_results import (
    load_self_consistency_flags,
    render_results_markdown,
    write_results_file,
)


class TestWriteResults:
    """Tests for write_results helpers."""

    def test_write_results_includes_caveats(self, tmp_path: Path) -> None:
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        (analysis_dir / "summary_tables.md").write_text("## tables", encoding="utf-8")
        content = render_results_markdown(analysis_dir, [], None)
        assert "gpt-5.4-nano" in content
        assert "gpt-6-luna" in content
        assert "provisional LLM labels" in content

    def test_write_results_flags_low_self_consistency(self, tmp_path: Path) -> None:
        scores_path = tmp_path / "scores.json"
        scores_path.write_text(
            json.dumps({"per_feature": {"cb_042": 0.85}, "features_below_threshold": ["cb_042"]}),
            encoding="utf-8",
        )
        flagged = load_self_consistency_flags(scores_path)
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        (analysis_dir / "summary_tables.md").write_text("", encoding="utf-8")
        content = render_results_markdown(analysis_dir, flagged, None)
        assert "cb_042" in content

    def test_write_results_main_writes_file(self, tmp_path: Path) -> None:
        analysis_dir = tmp_path / "analysis"
        analysis_dir.mkdir()
        (analysis_dir / "summary_tables.md").write_text("summary", encoding="utf-8")
        results_path = tmp_path / "RESULTS.md"
        write_results_file(analysis_dir, None, None, results_path)
        assert results_path.is_file()
