"""Tests for reflective dataset keys and feedback fields."""

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


class TestReflectiveDataset:
    """Tests for make_reflective_dataset."""

    def test_feedback_includes_remove_share_votes_and_study_key(self) -> None:
        scorer = FakeStudyFlipBatchScorer(probabilities_by_batch=[[0.9]])
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="plain_majority",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [
            JevDataInst(
                post_id="wrong-post",
                original_text="o",
                mirror_text="m",
                post_1_role="original",
                post_2_role="mirror",
                label=0,
                n_keep=7,
                n_remove=3,
                n_raters=10,
                remove_share=0.3,
                sampled_stance="left",
                sample_toxicity_type="low",
            )
        ]
        eval_batch = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=True,
        )

        dataset = adapter.make_reflective_dataset(
            {STUDY_COMPONENT_KEY: "seed study"},
            eval_batch,
            [STUDY_COMPONENT_KEY],
        )

        assert set(dataset) == {STUDY_COMPONENT_KEY}
        feedback = dataset[STUDY_COMPONENT_KEY][0]["Feedback"]
        assert "remove_share=0.300" in feedback
        assert "keep=7" in feedback
        assert "remove=3" in feedback
