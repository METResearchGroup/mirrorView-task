"""Tests for optimize runner helpers and smoke wiring."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import JevDataInst, JevGepaAdapter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize import (
    OptimizeConfig,
    run_optimize,
    select_candidate_on_dev,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.tests.fakes import FakeJevBatchScorer
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import probability_metrics


def _dev_inst(post_id: str, label: int) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text=f"{post_id}-original",
        mirror_text=f"{post_id}-mirror",
        post_1_role="original",
        post_2_role="mirror",
        label=label,
        n_keep=4,
        n_remove=6,
        n_raters=10,
        sampled_stance="liberal",
        sample_toxicity_type="insult",
    )


class TestSelectCandidateOnDev:
    """Tests for select_candidate_on_dev."""

    def test_selects_candidate_with_higher_dev_f1(self) -> None:
        devset = [_dev_inst("a", 1), _dev_inst("b", 0)]
        scorer = FakeJevBatchScorer(
            probabilities_by_batch=[[0.2, 0.8], [0.9, 0.1]],
        )
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        result = MagicMock()
        result.candidates = [
            {"instruction": "weak"},
            {"instruction": "strong"},
        ]

        idx, candidate, dev_f1 = select_candidate_on_dev(
            result,
            devset=devset,
            adapter=adapter,
        )

        expected_probs = [0.9, 0.1]
        expected_f1 = probability_metrics(
            [example.label for example in devset],
            expected_probs,
        ).f1

        assert idx == 1
        assert candidate == {"instruction": "strong"}
        assert dev_f1 == pytest.approx(expected_f1)


class TestRunOptimizeSmoke:
    """Tests for run_optimize smoke harness."""

    def test_smoke_writes_dev_selection_within_metric_budget(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "gepa_run"
        config = OptimizeConfig(
            ablation_id="B1_gepa_pair",
            view="pair",
            score_mode="probability",
            reflection_lm="openai/gpt-6-luna",
            max_reflection_cost=5.0,
            max_metric_calls=60,
            seed=20260924,
            run_dir=run_dir,
        )
        fake_result = MagicMock()
        fake_result.candidates = [{"instruction": "seed"}]
        fake_result.best_idx = 0
        fake_result.total_metric_calls = 10
        fake_result.to_dict.return_value = {"candidates": [{"instruction": "seed"}]}

        with (
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.gepa.optimize",
                return_value=fake_result,
            ) as mock_optimize,
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.load_gepa_splits",
                return_value=([], [], []),
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.load_seed_instruction",
                return_value="seed instruction",
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.select_candidate_on_dev",
                return_value=(0, {"instruction": "seed"}, 0.5),
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.init_run",
            ) as mock_init_run,
        ):
            mock_init_run.return_value = MagicMock()
            result = run_optimize(config, smoke=True)

        assert result.total_metric_calls <= 60
        dev_selection_path = tmp_path / "dev_selection.json"
        assert dev_selection_path.is_file()
        payload = json.loads(dev_selection_path.read_text(encoding="utf-8"))
        assert isinstance(payload["selected_candidate_idx"], int)
        assert mock_optimize.call_args.kwargs["reflection_lm"] == "openai/gpt-6-luna"

    def test_b1t_smoke_uses_terra_reflection_cost_cap(self, tmp_path: Path) -> None:
        run_dir = tmp_path / "gepa_run"
        config = OptimizeConfig(
            ablation_id="B1T_gepa_pair_terra",
            view="pair",
            score_mode="probability",
            reflection_lm="openai/gpt-5.6-terra",
            max_reflection_cost=20.0,
            max_metric_calls=60,
            seed=20260924,
            run_dir=run_dir,
        )
        fake_result = MagicMock()
        fake_result.candidates = [{"instruction": "seed"}]
        fake_result.best_idx = 0
        fake_result.total_metric_calls = 5
        fake_result.to_dict.return_value = {"candidates": [{"instruction": "seed"}]}

        with (
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.gepa.optimize",
                return_value=fake_result,
            ) as mock_optimize,
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.load_gepa_splits",
                return_value=([], [], []),
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.load_seed_instruction",
                return_value="seed instruction",
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.select_candidate_on_dev",
                return_value=(0, {"instruction": "seed"}, 0.5),
            ),
            patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.optimize.init_run",
            ) as mock_init_run,
        ):
            mock_init_run.return_value = MagicMock()
            run_optimize(config, smoke=True)

        assert mock_optimize.call_args.kwargs["max_reflection_cost"] == 20.0
