"""Tests for rebuilt GEPA test-split evaluation."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    DEV_SELECTION_FILENAME,
    GEPA_RESULT_FILENAME,
    GEPA_RUN_DIRNAME,
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate import (
    TEST_RESULTS_FILENAME,
    run_evaluate,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import BatchResult


def _write_ablation_artifacts(ablation_dir: Path, threshold: float) -> None:
    gepa_run = ablation_dir / GEPA_RUN_DIRNAME
    gepa_run.mkdir(parents=True, exist_ok=True)
    (ablation_dir / DEV_SELECTION_FILENAME).write_text(
        json.dumps(
            {
                "selected_candidate_idx": 0,
                "threshold": threshold,
                "dev_a_f1": 0.6,
                "dev_b_f1": 0.55,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    (gepa_run / GEPA_RESULT_FILENAME).write_text(
        json.dumps(
            {
                "candidates": [{STUDY_COMPONENT_KEY: "optimized instruction"}],
            }
        )
        + "\n",
        encoding="utf-8",
    )


def _parquet_fixture(path: Path) -> None:
    frame = pd.DataFrame(
        [
            {
                "post_id": "p1",
                "split": "test",
                "label": 1,
                "original_text": "orig one",
                "mirror_text": "mirror one",
                "post_1_role": "original",
                "post_2_role": "mirror",
                "n_keep": 1,
                "n_remove": 4,
                "n_raters": 5,
                "remove_share": 0.8,
                "sampled_stance": "liberal",
                "sample_toxicity_type": "none",
                "is_unanimous": False,
            },
            {
                "post_id": "p2",
                "split": "test",
                "label": 0,
                "original_text": "orig two",
                "mirror_text": "mirror two",
                "post_1_role": "original",
                "post_2_role": "mirror",
                "n_keep": 4,
                "n_remove": 1,
                "n_raters": 5,
                "remove_share": 0.2,
                "sampled_stance": "conservative",
                "sample_toxicity_type": "none",
                "is_unanimous": True,
            },
        ]
    )
    frame.to_parquet(path, index=False)


class TestEvaluateRebuilt:
    """Tests for run_evaluate on a test split."""

    def test_metrics_at_dev_threshold_and_default(self, tmp_path: Path) -> None:
        """Scores test split and writes metrics at dev threshold and 0.5."""
        ablation_dir = tmp_path / "R1_gepa_pair"
        _write_ablation_artifacts(ablation_dir, threshold=0.35)
        parquet_path = tmp_path / "cohort.parquet"
        _parquet_fixture(parquet_path)

        def fake_scorer(_client, state_texts, view, *, study_instruction, task_instruction=None):
            del view, study_instruction, task_instruction
            n = len(state_texts)
            probs = [0.45, 0.2][:n]
            if len(probs) < n:
                probs.extend([0.45] * (n - len(probs)))
            return BatchResult(
                probabilities=probs,
                latency_ms=100.0,
                input_tokens=50 * n,
                output_tokens=10 * n,
                model_version="test-model",
            )

        wandb_run = MagicMock()
        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate.upload_rebuilt",
        ):
            with patch(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate.init_run",
                return_value=wandb_run,
            ):
                with patch(
                    "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.evaluate.jev_scorer.build_client",
                    return_value=MagicMock(),
                ):
                    run_evaluate(
                        ablation_id="R1_gepa_pair",
                        split="test",
                        ablation_dir=ablation_dir,
                        cohort_parquet=parquet_path,
                        scorer=fake_scorer,
                        client=MagicMock(),
                    )

        results_path = ablation_dir / TEST_RESULTS_FILENAME
        assert results_path.is_file()
        payload = json.loads(results_path.read_text(encoding="utf-8"))
        assert payload["metrics_at_dev_threshold"]["threshold"] == 0.35
        assert payload["metrics_at_0_5"]["threshold"] == 0.5
        assert payload["metrics_at_dev_threshold"]["f1"] != payload["metrics_at_0_5"]["f1"]
        assert "roc_auc" in payload["metrics_at_dev_threshold"]
        assert "p50_ms" in payload["latency"]["request"]
