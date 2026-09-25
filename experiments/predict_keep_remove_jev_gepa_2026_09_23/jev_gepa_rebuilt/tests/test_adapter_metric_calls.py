"""Tests for post-count metric call accounting in the rebuilt adapter."""

from __future__ import annotations

from unittest.mock import MagicMock

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevDataInst,
    JevGepaRebuiltAdapter,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    STUDY_COMPONENT_KEY,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.tests.fakes import (
    FakeStudyFlipBatchScorer,
)


def _make_inst(post_id: str) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text="o",
        mirror_text="m",
        post_1_role="original",
        post_2_role="mirror",
        label=0,
        n_keep=8,
        n_remove=2,
        n_raters=10,
        remove_share=0.2,
        sampled_stance="left",
        sample_toxicity_type="low",
    )


class TestAdapterMetricCalls:
    """Tests for EvaluationBatch.num_metric_calls."""

    def test_counts_posts_not_http_batches(self) -> None:
        batch = [_make_inst(f"p{index}") for index in range(25)]
        scorer = FakeStudyFlipBatchScorer(
            probabilities_by_batch=[[0.5] * 10, [0.5] * 10, [0.5] * 5],
        )
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="plain_majority",
            scorer=scorer,
            client=MagicMock(),
            batch_size=10,
        )

        result = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=False,
        )

        assert len(result.outputs) == 25
        assert result.num_metric_calls == 25
        assert len(scorer.calls) == 3
