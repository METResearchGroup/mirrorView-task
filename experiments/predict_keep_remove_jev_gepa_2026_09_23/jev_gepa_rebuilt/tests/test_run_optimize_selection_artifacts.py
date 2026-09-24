"""Tests for run_optimize post-selection artifact writes."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    CANDIDATE_DEV_SCORES_FILENAME,
    DEV_SELECTION_FILENAME,
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import (
    OptimizeConfig,
    run_optimize,
)


def _fixture_gepa_result() -> GEPAResult:
    return GEPAResult(
        candidates=[
            {STUDY_COMPONENT_KEY: "seed"},
            {STUDY_COMPONENT_KEY: "c1"},
            {STUDY_COMPONENT_KEY: "c2"},
        ],
        parents=[[None], [0], [0]],
        val_aggregate_scores=[0.5, 0.9, 0.8],
        val_subscores=[{}, {0: 1.0}, {0: 1.0}],
        per_val_instance_best_candidates={},
        discovery_eval_counts=[0, 1, 1],
        total_metric_calls=10,
    )


class TestOptimizeWritesSelectionArtifacts:
    """Tests for dev selection artifacts after patched run_optimize."""

    def test_writes_dev_selection_and_stop_reason(self, tmp_path: Path) -> None:
        """Smoke run writes dev_selection.json, candidate scores, and stop_reason.json."""
        ablation_dir = tmp_path / "R1_gepa_pair"
        run_dir = ablation_dir / "gepa_run"
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
        acceptance_log = [
            {"candidate_idx": 1, "accepted": True, "reason": None},
            {"candidate_idx": 2, "accepted": True, "reason": None},
        ]

        reflection_lm = MagicMock()
        reflection_lm.total_tokens_in = 10
        reflection_lm.total_tokens_out = 5
        reflection_lm.total_cost = 0.01

        def fake_optimize(**kwargs: object) -> GEPAResult:
            log_path = Path(kwargs["run_dir"]) / "acceptance_log.jsonl"
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_path.write_text(
                "\n".join(json.dumps(row) for row in acceptance_log) + "\n",
                encoding="utf-8",
            )
            return _fixture_gepa_result()

        wandb_run = MagicMock()
        dev_split = {
            "seed": 20260924,
            "dev_a_ids": ["a1"],
            "dev_b_ids": ["b1"],
            "n_dev_a": 1,
            "n_dev_b": 1,
        }
        inst = MagicMock()
        inst.post_id = "a1"
        inst.label = 0

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.gepa.optimize",
            side_effect=fake_optimize,
        ):
            with patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.load_gepa_union_splits",
                return_value=([], []),
            ):
                with patch(
                    "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.build_or_load_dev_ab_split",
                    return_value=dev_split,
                ):
                    with patch(
                        "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.load_dev_instances",
                        return_value=[inst],
                    ):
                        with patch(
                            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.load_train_post_texts",
                            return_value=[],
                        ):
                            with patch(
                                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.make_reflection_lm_with_usage_log",
                                return_value=reflection_lm,
                            ):
                                with patch(
                                    "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.init_run",
                                    return_value=wandb_run,
                                ):
                                    with patch(
                                        "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.JevGepaRebuiltAdapter",
                                    ) as adapter_cls:
                                        adapter = MagicMock()
                                        from gepa.core.adapter import EvaluationBatch
                                        from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
                                            JevRolloutOutput,
                                        )

                                        adapter.evaluate.return_value = EvaluationBatch(
                                            outputs=[JevRolloutOutput(post_id="a1", p_remove=0.5)],
                                            scores=[0.5],
                                            trajectories=None,
                                            num_metric_calls=1,
                                        )
                                        adapter_cls.return_value = adapter
                                        with patch(
                                            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.upload_rebuilt",
                                        ):
                                            run_optimize(config, smoke=True)

        dev_selection_path = ablation_dir / DEV_SELECTION_FILENAME
        assert dev_selection_path.is_file()
        scores_path = ablation_dir / CANDIDATE_DEV_SCORES_FILENAME
        assert scores_path.is_file()
        score_lines = [
            line for line in scores_path.read_text(encoding="utf-8").splitlines() if line.strip()
        ]
        assert len(score_lines) <= 10
        stop_reason_path = run_dir / "stop_reason.json"
        assert stop_reason_path.is_file()
        stop_payload = json.loads(stop_reason_path.read_text(encoding="utf-8"))
        assert "stop_reason" in stop_payload
