"""Tests for batched Jev scorer."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared import jev_scorer
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.jev_scorer import (
    PostPrediction,
    PostTask,
    score_batch,
    run_scoring_pass,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.prompt import POSTS_STATE_KEY
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.tests.conftest import (
    FakeTypeSafeClient,
    FakeUsage,
)


OPTIMIZED_PROMPT = "OPTIMIZED_PROMPT"


class TestScoreBatch:
    """Tests for score_batch and run_scoring_pass."""

    def test_score_batch_returns_probabilities_and_tokens(self) -> None:
        client = FakeTypeSafeClient(
            answers={0: 0.7, 1: 0.3},
            usage=FakeUsage(input_tokens=42, output_tokens=7),
        )
        result = score_batch(client, ["state-0", "state-1"], "pair")
        assert result.probabilities == [0.7, 0.3]
        assert result.input_tokens == 42
        assert result.output_tokens == 7

    def test_score_batch_with_custom_instruction(self) -> None:
        client = FakeTypeSafeClient(
            answers={0: 0.7, 1: 0.3},
            usage=FakeUsage(input_tokens=42, output_tokens=7),
        )
        result = score_batch(
            client,
            ["state-0", "state-1"],
            "pair",
            instruction=OPTIMIZED_PROMPT,
        )
        assert result.probabilities == [0.7, 0.3]
        post_0_instruction = client.calls[0]["questions"]["post_0"].instructions
        post_1_instruction = client.calls[0]["questions"]["post_1"].instructions
        assert post_0_instruction.startswith(f"Consider `{POSTS_STATE_KEY}[0]`.")
        assert OPTIMIZED_PROMPT in post_0_instruction
        assert post_1_instruction.startswith(f"Consider `{POSTS_STATE_KEY}[1]`.")
        assert OPTIMIZED_PROMPT in post_1_instruction

    def test_run_scoring_pass_resumes_existing_predictions(self, tmp_path: Path) -> None:
        predictions_path = tmp_path / "predictions.jsonl"
        seeded = PostPrediction(
            post_id="A",
            view="pair",
            gold_label=0,
            probability_remove=0.1,
            batch_size=10,
            request_index=0,
            position_in_request=0,
            n_posts_in_request=1,
            request_latency_ms=10.0,
            per_post_latency_ms=10.0,
            request_input_tokens=10,
            request_output_tokens=1,
            per_post_input_tokens=10.0,
            per_post_output_tokens=1.0,
            estimated_cost_usd=0.0,
            model_version="jev-1.13.0",
            attempts=1,
        )
        predictions_path.write_text(seeded.model_dump_json() + "\n", encoding="utf-8")

        client = FakeTypeSafeClient(
            answers={0: 0.2, 1: 0.8},
            usage=FakeUsage(input_tokens=20, output_tokens=2),
        )
        tasks = [
            PostTask(post_id="A", state_text="a", gold_label=0),
            PostTask(post_id="B", state_text="b", gold_label=1),
            PostTask(post_id="C", state_text="c", gold_label=1),
        ]

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(jev_scorer, "build_client", lambda api_key: client)
            run_scoring_pass(tasks, tmp_path, view="pair", api_key="test-key")

        lines = predictions_path.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 3
        post_ids = [json.loads(line)["post_id"] for line in lines]
        assert post_ids.count("A") == 1
        assert "B" in post_ids
        assert "C" in post_ids
        assert client.call_count == 1

    def test_run_scoring_pass_per_post_fields_for_batch_of_ten(self, tmp_path: Path) -> None:
        client = FakeTypeSafeClient(
            answers={index: 0.5 for index in range(10)},
            usage=FakeUsage(input_tokens=100, output_tokens=10),
        )
        tasks = [
            PostTask(post_id=f"P{index}", state_text=f"state-{index}", gold_label=0)
            for index in range(10)
        ]

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(jev_scorer, "build_client", lambda api_key: client)
            run_scoring_pass(tasks, tmp_path, view="pair", api_key="test-key")

        predictions = [
            PostPrediction.model_validate(json.loads(line))
            for line in (tmp_path / "predictions.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        for prediction in predictions:
            assert prediction.per_post_latency_ms == prediction.request_latency_ms / 10
            assert prediction.per_post_input_tokens == prediction.request_input_tokens / 10
            assert prediction.per_post_output_tokens == prediction.request_output_tokens / 10

    def test_run_scoring_pass_writes_deadletter_after_exhausted_retries(self, tmp_path: Path) -> None:
        client = FakeTypeSafeClient(
            answers={0: 0.5},
            fail_with=RuntimeError("boom"),
            fail_times=4,
        )
        tasks = [PostTask(post_id="P1", state_text="state", gold_label=1)]

        with pytest.MonkeyPatch.context() as monkeypatch:
            monkeypatch.setattr(jev_scorer, "build_client", lambda api_key: client)
            run_scoring_pass(tasks, tmp_path, view="pair", api_key="test-key")

        deadletter_path = tmp_path / "deadletter.jsonl"
        assert deadletter_path.is_file()
        records = [
            json.loads(line)
            for line in deadletter_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        assert len(records) == 1
        assert records[0]["status"] == "error"
        assert records[0]["error_type"] == "RuntimeError"
