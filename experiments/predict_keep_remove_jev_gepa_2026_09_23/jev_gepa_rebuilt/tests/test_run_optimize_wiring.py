"""Tests for run_optimize GEPA hook wiring."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    REFLECTION_MINIBATCH_SIZE,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize import (
    GuardedHardLabelAcceptance,
    OptimizeConfig,
    run_optimize,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.error_focused_sampler import (
    ErrorFocusedBatchSampler,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.hard_label_acceptance import (
    HardLabelMarginAcceptance,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.val_subsample_on_accept import (
    ValSubsampleOnAcceptPolicy,
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


class TestRunOptimizeWiring:
    """Tests for run_optimize passing custom GEPA policies."""

    def test_smoke_r1_passes_custom_hooks(self) -> None:
        """Smoke R1 run wires rebuilt policies into gepa.optimize."""
        config = OptimizeConfig(
            ablation_id="R1_gepa_pair",
            view="pair",
            score_mode="label_certainty",
            reflection_lm="openai/gpt-6-luna",
            max_reflection_cost=5.0,
            max_metric_calls=120,
            seed=20260924,
            run_dir=Path("/tmp/r1_smoke_gepa_run"),
            val_subsample_size=20,
        )
        captured: dict = {}

        def fake_optimize(**kwargs: object) -> GEPAResult:
            captured.update(kwargs)
            return _minimal_gepa_result()

        wandb_run = MagicMock()
        reflection_lm = MagicMock()
        reflection_lm.total_cost = 0.0
        reflection_lm.total_tokens_in = 0
        reflection_lm.total_tokens_out = 0
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
                    return_value={"dev_a_ids": [], "dev_b_ids": []},
                ):
                    with patch(
                        "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.load_dev_instances",
                        return_value=[],
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
                                    ):
                                        with patch(
                                            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.upload_rebuilt",
                                        ):
                                            with patch(
                                                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.optimize.select_on_dev_ab",
                                                return_value=(0, 0.5, 0.0, 0.0, []),
                                            ):
                                                run_optimize(config, smoke=True)

        assert isinstance(captured["acceptance_criterion"], GuardedHardLabelAcceptance)
        assert isinstance(captured["val_evaluation_policy"], ValSubsampleOnAcceptPolicy)
        assert isinstance(captured["batch_sampler"], ErrorFocusedBatchSampler)
        assert captured["batch_sampler"].minibatch_size == REFLECTION_MINIBATCH_SIZE
        assert captured["use_merge"] is False
        assert "module_selector" not in captured
