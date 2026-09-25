"""Tests for rebuilt adapter score modes R1, R2, and R7."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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


def _make_inst(
    *,
    label: int,
    remove_share: float,
    n_keep: int,
    n_remove: int,
    post_id: str = "p1",
) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text="o",
        mirror_text="m",
        post_1_role="original",
        post_2_role="mirror",
        label=label,
        n_keep=n_keep,
        n_remove=n_remove,
        n_raters=n_keep + n_remove,
        remove_share=remove_share,
        sampled_stance="left",
        sample_toxicity_type="low",
    )


class TestAdapterScoreModes:
    """Tests for label_certainty, majority_weighted, and plain_majority scoring."""

    def test_label_certainty_matches_remove_share(self) -> None:
        scorer = FakeStudyFlipBatchScorer(probabilities_by_batch=[[0.75]])
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="label_certainty",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst(label=1, remove_share=0.8, n_keep=2, n_remove=8)]

        result = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=False,
        )

        assert result.scores[0] == pytest.approx(0.95)

    def test_majority_weighted_applies_one_vote_margin_weight(self) -> None:
        scorer = FakeStudyFlipBatchScorer(probabilities_by_batch=[[0.4]])
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="majority_weighted",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst(label=0, remove_share=0.4, n_keep=3, n_remove=2)]

        result = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=False,
        )

        assert result.scores[0] == pytest.approx(0.3)

    def test_plain_majority_uses_full_weight(self) -> None:
        scorer = FakeStudyFlipBatchScorer(probabilities_by_batch=[[0.4]])
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="plain_majority",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst(label=0, remove_share=0.4, n_keep=3, n_remove=2)]

        result = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=False,
        )

        assert result.scores[0] == pytest.approx(0.6)

    def test_majority_weighted_one_vote_margin_uses_half_weight(self) -> None:
        scorer = FakeStudyFlipBatchScorer(probabilities_by_batch=[[0.2]])
        adapter = JevGepaRebuiltAdapter(
            view="pair",
            score_mode="majority_weighted",
            scorer=scorer,
            client=MagicMock(),
        )
        batch = [_make_inst(label=0, remove_share=0.45, n_keep=5, n_remove=4)]

        result = adapter.evaluate(
            batch,
            {STUDY_COMPONENT_KEY: "seed study"},
            capture_traces=False,
        )

        assert result.scores[0] == pytest.approx(0.4)
