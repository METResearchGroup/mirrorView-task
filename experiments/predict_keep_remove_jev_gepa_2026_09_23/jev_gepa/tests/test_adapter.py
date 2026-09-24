"""Tests for JevGepaAdapter.evaluate and make_reflective_dataset."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter import (
    JevDataInst,
    JevGepaAdapter,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.tests.fakes import FakeJevBatchScorer


def _make_inst(
    post_id: str,
    *,
    label: int = 1,
    original_text: str = "original",
    mirror_text: str = "mirror",
) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text=original_text,
        mirror_text=mirror_text,
        post_1_role="original",
        post_2_role="mirror",
        label=label,
        n_keep=3,
        n_remove=7,
        n_raters=10,
        sampled_stance="conservative",
        sample_toxicity_type="none",
    )


class TestJevGepaAdapterEvaluate:
    """Tests for JevGepaAdapter.evaluate."""

    def test_batches_twelve_examples_with_two_metric_calls(self) -> None:
        batch = [_make_inst(f"post-{index}") for index in range(12)]
        scorer = FakeJevBatchScorer(
            probabilities_by_batch=[[0.5] * 10, [0.5] * 2],
        )
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        candidate = {"instruction": "CAND"}

        result = adapter.evaluate(batch, candidate, capture_traces=False)

        assert len(result.outputs) == 12
        assert len(result.scores) == 12
        assert result.num_metric_calls == 2
        assert all(call["instruction"] == "CAND" for call in scorer.calls)

    def test_probability_mode_scores_gold_label_probability(self) -> None:
        scorer = FakeJevBatchScorer(
            probabilities_by_batch=[[0.9, 0.1]],
        )
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        batch = [
            _make_inst("remove-post", label=1),
            _make_inst("keep-post", label=0),
        ]

        result = adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=False)

        assert result.scores[0] == pytest.approx(0.9)
        assert result.scores[1] == pytest.approx(0.9)

    def test_scorer_failure_raises_without_fallback(self) -> None:
        scorer = FakeJevBatchScorer(raise_on_post_index=1)
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        batch = [_make_inst("ok-post"), _make_inst("bad-post")]

        with pytest.raises(ValueError, match="scorer failed for batch size"):
            adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=True)

    def test_scorer_uses_run_with_retries(self) -> None:
        scorer = FakeJevBatchScorer(probabilities_by_batch=[[0.5, 0.5]])
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        batch = [_make_inst("post-a"), _make_inst("post-b")]

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa.adapter.run_with_retries",
            wraps=__import__(
                "experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.retries",
                fromlist=["run_with_retries"],
            ).run_with_retries,
        ) as mock_retries:
            adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=False)

        mock_retries.assert_called_once()


class TestJevGepaAdapterReflectiveDataset:
    """Tests for JevGepaAdapter.make_reflective_dataset."""

    def test_feedback_includes_gold_vote_stance_toxicity_threshold(self) -> None:
        scorer = FakeJevBatchScorer(probabilities_by_batch=[[0.9]])
        adapter = JevGepaAdapter(view="pair", scorer=scorer, client=MagicMock())
        batch = [_make_inst("post-1", label=1)]
        eval_batch = adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=True)

        dataset = adapter.make_reflective_dataset(
            {"instruction": "seed"},
            eval_batch,
            ["instruction"],
        )

        feedback = dataset["instruction"][0]["Feedback"]
        assert "gold label" in feedback.lower() or "label=1" in feedback.lower()
        assert "keep" in feedback.lower()
        assert "remove" in feedback.lower()
        assert "stance" in feedback.lower()
        assert "toxicity" in feedback.lower()
        assert "threshold" in feedback.lower()


class TestAsymmetricReward:
    """Tests for asymmetric reward scoring mode."""

    def test_false_negative_scores_minus_three(self) -> None:
        scorer = FakeJevBatchScorer(probabilities_by_batch=[[0.4]])
        adapter = JevGepaAdapter(
            view="pair",
            score_mode="asymmetric",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst("post-1", label=1)]

        result = adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=False)

        assert result.scores[0] == pytest.approx(-3.0)

    def test_true_negative_scores_plus_half(self) -> None:
        scorer = FakeJevBatchScorer(probabilities_by_batch=[[0.1]])
        adapter = JevGepaAdapter(
            view="pair",
            score_mode="asymmetric",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst("post-1", label=0)]

        result = adapter.evaluate(batch, {"instruction": "seed"}, capture_traces=False)

        assert result.scores[0] == pytest.approx(0.5)
