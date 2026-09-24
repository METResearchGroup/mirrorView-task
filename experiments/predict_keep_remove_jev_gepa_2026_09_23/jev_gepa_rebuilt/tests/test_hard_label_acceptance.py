"""Tests for HardLabelMarginAcceptance."""

from __future__ import annotations

from unittest.mock import MagicMock

from gepa.proposer.base import CandidateProposal, SubsampleEvaluation

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevTrajectory
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.hard_label_acceptance import (
    HardLabelMarginAcceptance,
)


def _trajectories(correct_count: int, total: int = 25) -> list[JevTrajectory]:
    trajectories: list[JevTrajectory] = []
    for index in range(total):
        label = 1
        p_remove = 0.9 if index < correct_count else 0.1
        trajectories.append(
            JevTrajectory(
                post_id=str(index),
                view="pair",
                study_instruction="seed",
                original_text="o",
                mirror_text="m",
                p_remove=p_remove,
                label=label,
                n_keep=5,
                n_remove=5,
                remove_share=0.5,
                sampled_stance="left",
                sample_toxicity_type="low",
                threshold_crossed=True,
            )
        )
    return trajectories


def _proposal(correct_before: int, correct_after: int) -> CandidateProposal:
    return CandidateProposal(
        candidate={"study_instruction": "child"},
        parent_program_ids=[0],
        eval_before=SubsampleEvaluation(
            scores=[1.0] * 25,
            trajectories=_trajectories(correct_before),
        ),
        eval_after=SubsampleEvaluation(
            scores=[1.0] * 25,
            trajectories=_trajectories(correct_after),
        ),
    )


class TestHardLabelMarginAcceptance:
    """Tests for HardLabelMarginAcceptance.should_accept."""

    def test_margin_plus_one_rejects(self) -> None:
        """Child +1 correct vs parent is below +2 margin."""
        acceptance = HardLabelMarginAcceptance()
        state = MagicMock()
        proposal = _proposal(correct_before=10, correct_after=11)
        result = acceptance.should_accept(proposal, state)
        assert result is False

    def test_margin_plus_two_accepts(self) -> None:
        """Child +2 correct vs parent meets margin."""
        acceptance = HardLabelMarginAcceptance()
        state = MagicMock()
        proposal = _proposal(correct_before=10, correct_after=12)
        result = acceptance.should_accept(proposal, state)
        assert result is True

    def test_equal_correct_rejects(self) -> None:
        """Equal hard-label accuracy does not accept."""
        acceptance = HardLabelMarginAcceptance()
        state = MagicMock()
        proposal = _proposal(correct_before=12, correct_after=12)
        result = acceptance.should_accept(proposal, state)
        assert result is False
