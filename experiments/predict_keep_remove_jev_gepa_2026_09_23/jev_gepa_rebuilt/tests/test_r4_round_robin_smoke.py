"""Tests for R4 round-robin component update log checks."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    R4_ROUND_ROBIN_COMPONENT_KEYS,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.smoke_checks import (
    evaluate_r4_round_robin_smoke,
)

_SEED_HASHES = {
    "study_instruction": "hash_a",
    "remove_criteria": "hash_b",
    "keep_criteria": "hash_c",
    "mirror_note": "hash_d",
}


class TestR4RoundRobinLog:
    """Tests for evaluate_r4_round_robin_smoke."""

    def test_passes_with_cycle_and_three_hash_changes(self, tmp_path: Path) -> None:
        """Eight iterations cycling four keys with three mutations passes."""
        log_path = _write_log(
            tmp_path,
            [
                ("study_instruction", "hash_a2"),
                ("remove_criteria", "hash_b2"),
                ("keep_criteria", "hash_c2"),
                ("mirror_note", "hash_d"),
                ("study_instruction", "hash_a3"),
                ("remove_criteria", "hash_b3"),
                ("keep_criteria", "hash_c3"),
                ("mirror_note", "hash_d"),
            ],
        )
        result = evaluate_r4_round_robin_smoke(tmp_path, log_path=log_path)
        assert result["passed"] is True

    def test_fails_when_only_one_key_mutates(self, tmp_path: Path) -> None:
        """Only study_instruction hash changes fails the criterion."""
        log_path = _write_log(
            tmp_path,
            [
                ("study_instruction", "hash_a2"),
                ("remove_criteria", "hash_b"),
                ("keep_criteria", "hash_c"),
                ("mirror_note", "hash_d"),
                ("study_instruction", "hash_a3"),
                ("remove_criteria", "hash_b"),
                ("keep_criteria", "hash_c"),
                ("mirror_note", "hash_d"),
            ],
        )
        result = evaluate_r4_round_robin_smoke(tmp_path, log_path=log_path)
        assert result["passed"] is False


def _write_log(tmp_path: Path, rows: list[tuple[str, str]]) -> Path:
    run_dir = tmp_path / "R4_gepa_multi_component" / "gepa_run"
    run_dir.mkdir(parents=True)
    log_path = run_dir / "component_update_log.jsonl"
    with log_path.open("w", encoding="utf-8") as handle:
        for key in R4_ROUND_ROBIN_COMPONENT_KEYS:
            handle.write(
                json.dumps(
                    {
                        "iteration": 0,
                        "module_selected": key,
                        "keys_snapshot_hash": _SEED_HASHES[key],
                    }
                )
                + "\n"
            )
        for iteration, (module_selected, keys_snapshot_hash) in enumerate(rows, start=1):
            record = {
                "iteration": iteration,
                "module_selected": module_selected,
                "keys_snapshot_hash": keys_snapshot_hash,
            }
            handle.write(json.dumps(record) + "\n")
    return log_path
