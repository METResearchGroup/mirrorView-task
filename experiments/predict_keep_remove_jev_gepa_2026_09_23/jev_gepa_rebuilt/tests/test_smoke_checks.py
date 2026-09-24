"""Tests for GEPA smoke pass criteria."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.smoke_checks import (
    assert_r1_smoke_pass,
)


class TestSmokeChecks:
    """Tests for assert_r1_smoke_pass."""

    def test_passes_with_reject_and_reflection_usd(self, tmp_path: Path) -> None:
        """Fixture with one reject and reflection USD returns passed true."""
        run_dir = tmp_path / "R1_gepa_pair" / "gepa_run"
        run_dir.mkdir(parents=True)
        (run_dir / "gepa_result.json").write_text(
            json.dumps({"total_metric_calls": 100, "parents": [[0], [1]]}),
            encoding="utf-8",
        )
        (run_dir / "stop_reason.json").write_text(
            json.dumps({"stop_reason": "max_metric_calls", "reflection_cost_usd": 0.02}),
            encoding="utf-8",
        )
        (run_dir / "acceptance_log.jsonl").write_text(
            json.dumps({"candidate_idx": 1, "accepted": False, "reason": "margin"}) + "\n",
            encoding="utf-8",
        )
        (run_dir / "reflection_usage.jsonl").write_text(
            json.dumps({"usd": 0.01}) + "\n",
            encoding="utf-8",
        )

        report = assert_r1_smoke_pass(tmp_path / "R1_gepa_pair")

        assert report["passed"] is True

    def test_raises_without_reject_or_reflection(self, tmp_path: Path) -> None:
        """Missing reject and reflection USD raises AssertionError."""
        run_dir = tmp_path / "R1_gepa_pair" / "gepa_run"
        run_dir.mkdir(parents=True)
        (run_dir / "gepa_result.json").write_text(
            json.dumps({"total_metric_calls": 50, "parents": [[0]]}),
            encoding="utf-8",
        )
        (run_dir / "stop_reason.json").write_text(
            json.dumps({"stop_reason": "max_metric_calls", "reflection_cost_usd": 0.0}),
            encoding="utf-8",
        )
        (run_dir / "acceptance_log.jsonl").write_text(
            json.dumps({"candidate_idx": 1, "accepted": True, "reason": None}) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(AssertionError):
            assert_r1_smoke_pass(tmp_path / "R1_gepa_pair")
