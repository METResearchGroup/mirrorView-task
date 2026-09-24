"""Tests for Jev scoring failure stopping optimize runs."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.errors import JevScoringFailed
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import (
    OptimizeConfig,
    run_optimize,
)


def _minimal_gepa_result() -> GEPAResult:
    return GEPAResult(
        candidates=[{"study_instruction": "seed"}],
        parents=[[None]],
        val_aggregate_scores=[0.0],
        val_subscores=[{}],
        per_val_instance_best_candidates={},
        discovery_eval_counts=[0],
        total_metric_calls=0,
    )


class TestJevFailureStops:
    """Tests for run_optimize handling JevScoringFailed."""

    def test_writes_jev_failure_and_exits(self, tmp_path: Path) -> None:
        """Jev failure during optimize writes jev_failure.json and exits 2."""
        run_dir = tmp_path / "R1_gepa_pair" / "gepa_run"
        config = OptimizeConfig(
            ablation_id="R1_gepa_pair",
            view="pair",
            score_mode="label_certainty",
            reflection_lm="openai/gpt-6-luna",
            max_reflection_cost=5.0,
            max_metric_calls=120,
            seed=20260924,
            run_dir=run_dir,
            val_subsample_size=20,
        )
        failure = JevScoringFailed("jev down", post_id="post-99", batch_idx=2)

        def fake_optimize(**kwargs: object) -> GEPAResult:
            adapter = kwargs["adapter"]
            adapter.evaluate([], {"study_instruction": "x"})
            adapter.evaluate([], {"study_instruction": "x"})
            return _minimal_gepa_result()

        adapter_instance = MagicMock()
        adapter_instance.evaluate.side_effect = [MagicMock(), failure]

        wandb_run = MagicMock()
        wandb_run.summary = {}
        reflection_lm = MagicMock()
        reflection_lm.total_cost = 0.0
        reflection_lm.total_tokens_in = 0
        reflection_lm.total_tokens_out = 0

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.gepa.optimize",
            side_effect=fake_optimize,
        ):
            with patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.JevGepaRebuiltAdapter",
                return_value=adapter_instance,
            ):
                with patch(
                    "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.load_gepa_union_splits",
                    return_value=([], []),
                ):
                    with patch(
                        "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.build_or_load_dev_ab_split",
                        return_value={"dev_a_ids": [], "dev_b_ids": []},
                    ):
                        with patch(
                            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.make_reflection_lm_with_usage_log",
                            return_value=reflection_lm,
                        ):
                            with patch(
                                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.init_run",
                                return_value=wandb_run,
                            ):
                                with pytest.raises(SystemExit) as exc_info:
                                    run_optimize(config, smoke=True)

        assert exc_info.value.code == 2
        failure_path = run_dir / "jev_failure.json"
        assert failure_path.is_file()
        payload = json.loads(failure_path.read_text(encoding="utf-8"))
        assert payload["batch_idx"] == 2
        assert payload["post_id"] == "post-99"
        assert wandb_run.summary["status"] == "jev_failed"
