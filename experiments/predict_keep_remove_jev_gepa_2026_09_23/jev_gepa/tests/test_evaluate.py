"""Tests for GEPA evaluate runner."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate import (
    EvalConfig,
    compare_b1_b1t,
    evaluate_instruction,
    finalize_eval_output,
    load_selected_instruction,
    resolve_transfer_eval_config,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.tests.fakes import FakeJevBatchScorer


def _write_dev_selection_fixture(ablation_dir: Path, selected_idx: int) -> None:
    ablation_dir.mkdir(parents=True, exist_ok=True)
    gepa_run_dir = ablation_dir / "gepa_run"
    gepa_run_dir.mkdir(parents=True, exist_ok=True)
    candidates = [
        {"instruction": "candidate zero"},
        {"instruction": "candidate one"},
        {"instruction": "candidate two"},
    ]
    (gepa_run_dir / "candidates.json").write_text(json.dumps(candidates), encoding="utf-8")
    (ablation_dir / "dev_selection.json").write_text(
        json.dumps({"selected_candidate_idx": selected_idx, "selected_dev_f1": 0.5}),
        encoding="utf-8",
    )


class TestLoadSelectedInstruction:
    """Tests for load_selected_instruction."""

    def test_returns_selected_candidate_instruction(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        ablation_dir = tmp_path / "B1_gepa_pair"
        _write_dev_selection_fixture(ablation_dir, selected_idx=2)
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate._ablation_output_dir",
            lambda ablation_id: ablation_dir,
        )

        result = load_selected_instruction("B1_gepa_pair")

        assert result == "candidate two"


class TestEvaluateInstruction:
    """Tests for evaluate_instruction."""

    def test_writes_results_and_parquet_for_test_split(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        cohort = pd.DataFrame(
            {
                "post_id": ["post-a", "post-b"],
                "original_text": ["orig-a", "orig-b"],
                "mirror_text": ["mir-a", "mir-b"],
                "post_1_role": ["original", "original"],
                "post_2_role": ["mirror", "mirror"],
                "label": [1, 0],
                "split": ["test", "test"],
                "sampled_stance": ["liberal", "conservative"],
                "sample_toxicity_type": ["insult", "threat"],
                "remove_share": [0.8, 0.2],
                "is_unanimous": [False, True],
                "n_raters": [10, 10],
            }
        )
        output_dir = tmp_path / "test_eval"
        scorer = FakeJevBatchScorer(probabilities_by_batch=[[0.9], [0.1]])

        def _fake_run_scoring_pass(
            tasks: list[object],
            out_dir: Path,
            **kwargs: object,
        ) -> object:
            out_dir.mkdir(parents=True, exist_ok=True)
            predictions_path = out_dir / "predictions.jsonl"
            requests_path = out_dir / "requests.jsonl"
            for index, task in enumerate(tasks):
                prediction = {
                    "post_id": task.post_id,
                    "view": kwargs["view"],
                    "gold_label": task.gold_label,
                    "probability_remove": scorer(
                        MagicMock(),
                        [task.state_text],
                        str(kwargs["view"]),
                        instruction=str(kwargs["instruction"]),
                    ).probabilities[0],
                    "batch_size": 1,
                    "request_index": 0,
                    "position_in_request": index,
                    "n_posts_in_request": len(tasks),
                    "request_latency_ms": 10.0,
                    "per_post_latency_ms": 10.0,
                    "request_input_tokens": 100,
                    "request_output_tokens": 10,
                    "per_post_input_tokens": 100.0,
                    "per_post_output_tokens": 10.0,
                    "estimated_cost_usd": 0.001,
                    "model_version": "fake-jev",
                    "attempts": 1,
                }
                predictions_path.open("a", encoding="utf-8").write(
                    json.dumps(prediction) + "\n"
                )
            requests_path.write_text(
                json.dumps(
                    {
                        "request_id": "req-0",
                        "ablation_id": kwargs.get("ablation_id", ""),
                        "batch_index": 0,
                        "post_ids": [task.post_id for task in tasks],
                        "n_posts": len(tasks),
                        "attempt": 1,
                        "status": "ok",
                        "error_type": None,
                        "started_at_utc": "2026-09-24T00:00:00+00:00",
                        "latency_ms": 10.0,
                        "latency_per_post_ms": 5.0,
                        "input_tokens": 100,
                        "output_tokens": 10,
                        "estimated_cost_usd": 0.001,
                        "model": "fake-jev",
                        "instruction_sha256": "abc123",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            return MagicMock()

        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate._load_cohort",
            lambda _path: cohort,
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer.run_scoring_pass",
            _fake_run_scoring_pass,
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate.init_run",
            lambda spec: MagicMock(finish=MagicMock()),
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate.log_artifact",
            lambda *args, **kwargs: None,
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate.secrets.get_jev_api_key",
            lambda: "test-key",
        )

        config = EvalConfig(
            ablation_id="B1_gepa_pair",
            transfer_id=None,
            instruction="fixed instruction",
            view="pair",
            split="test",
            output_dir=output_dir,
        )
        results = evaluate_instruction(config)

        labels = pd.read_parquet(output_dir / "labels.parquet")
        requests = pd.read_parquet(output_dir / "requests.parquet")

        assert results["headline_split"] == "test"
        assert len(labels) == 2
        assert "latency_ms" in requests.columns
        assert "latency_per_post_ms" in requests.columns
        assert "estimated_cost_usd" in requests.columns
        assert "instruction_sha256" in requests.columns
        assert scorer.calls[0]["instruction"] == "fixed instruction"

    def test_transfer_config_uses_b1_prompt_on_original_view(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        b1_dir = tmp_path / "B1_gepa_pair"
        _write_dev_selection_fixture(b1_dir, selected_idx=1)
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate._ablation_output_dir",
            lambda ablation_id: b1_dir,
        )
        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate.OUTPUT_ROOT",
            tmp_path,
        )

        config = resolve_transfer_eval_config("transfer_B1_on_original", "dev")

        assert config.view == "original"
        assert config.instruction == "candidate one"


class TestCompareB1B1t:
    """Tests for compare_b1_b1t."""

    def test_returns_dev_test_f1_and_reflection_cost(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        for ablation_id, dev_f1, test_f1, reflection_cost in [
            ("B1_gepa_pair", 0.51, 0.49, 4.5),
            ("B1T_gepa_pair_terra", 0.55, 0.52, 18.0),
        ]:
            ablation_dir = tmp_path / ablation_id
            ablation_dir.mkdir(parents=True, exist_ok=True)
            (ablation_dir / "dev_selection.json").write_text(
                json.dumps(
                    {
                        "selected_dev_f1": dev_f1,
                        "reflection_cost_usd": reflection_cost,
                    }
                ),
                encoding="utf-8",
            )
            test_eval_dir = ablation_dir / "test_eval"
            test_eval_dir.mkdir(parents=True, exist_ok=True)
            (test_eval_dir / "results.json").write_text(
                json.dumps({"split_metrics": {"test": {"f1": test_f1}}}),
                encoding="utf-8",
            )

        monkeypatch.setattr(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.evaluate._ablation_output_dir",
            lambda ablation_id: tmp_path / ablation_id,
        )

        result = compare_b1_b1t()

        assert set(result.keys()) == {"B1_gepa_pair", "B1T_gepa_pair_terra"}
        assert result["B1_gepa_pair"] == {
            "dev_f1": 0.51,
            "test_f1": 0.49,
            "reflection_cost_usd": 4.5,
        }
        assert result["B1T_gepa_pair_terra"] == {
            "dev_f1": 0.55,
            "test_f1": 0.52,
            "reflection_cost_usd": 18.0,
        }


class TestFinalizeEvalOutput:
    """Tests for finalize_eval_output."""

    def test_raises_when_prediction_count_does_not_match_cohort(self, tmp_path: Path) -> None:
        cohort = pd.DataFrame(
            {
                "post_id": ["post-a", "post-b"],
                "split": ["test", "test"],
                "label": [1, 0],
                "sampled_stance": ["liberal", "conservative"],
                "sample_toxicity_type": ["insult", "threat"],
                "remove_share": [0.8, 0.2],
                "is_unanimous": [False, True],
                "n_raters": [10, 10],
            }
        )
        output_dir = tmp_path / "test_eval"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "predictions.jsonl").write_text(
            json.dumps({"post_id": "post-a", "probability_remove": 0.9}) + "\n",
            encoding="utf-8",
        )

        with pytest.raises(RuntimeError, match="1/2 rows scored; 1 missing"):
            finalize_eval_output(
                output_dir,
                cohort,
                ablation_id="B1_gepa_pair",
                headline_split="test",
            )

    def test_sets_dev_tuned_test_metrics_null_without_dev_split(self, tmp_path: Path) -> None:
        cohort = pd.DataFrame(
            {
                "post_id": ["post-a"],
                "split": ["test"],
                "label": [1],
                "sampled_stance": ["liberal"],
                "sample_toxicity_type": ["insult"],
                "remove_share": [0.8],
                "is_unanimous": [False],
                "n_raters": [10],
            }
        )
        output_dir = tmp_path / "test_eval"
        output_dir.mkdir(parents=True, exist_ok=True)
        (output_dir / "predictions.jsonl").write_text(
            json.dumps({"post_id": "post-a", "probability_remove": 0.9}) + "\n",
            encoding="utf-8",
        )
        (output_dir / "requests.jsonl").write_text(
            json.dumps(
                {
                    "request_id": "req-0",
                    "status": "ok",
                    "latency_ms": 10.0,
                    "latency_per_post_ms": 10.0,
                    "input_tokens": 10,
                    "output_tokens": 1,
                    "estimated_cost_usd": 0.001,
                }
            )
            + "\n",
            encoding="utf-8",
        )

        results = finalize_eval_output(
            output_dir,
            cohort,
            ablation_id="B1_gepa_pair",
            headline_split="test",
        )

        assert results["dev_tuned_test_metrics"] is None
