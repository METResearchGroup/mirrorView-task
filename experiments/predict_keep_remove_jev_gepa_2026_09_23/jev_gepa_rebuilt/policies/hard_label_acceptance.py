"""Hard-label acceptance on the reflection minibatch (+2 correct margin).

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_hard_label_acceptance.py -q

Parent and child are scored on the same 25-post minibatch before ``should_accept``
(50 posts total per proposal). Acceptance uses threshold 0.5 hard labels, not soft
score sums from the adapter.
"""

from __future__ import annotations

from gepa.core.state import GEPAState
from gepa.proposer.base import CandidateProposal

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevRolloutOutput,
    JevTrajectory,
    REMOVE_LABEL,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import ACCEPTANCE_MARGIN_CORRECT

HARD_LABEL_THRESHOLD = 0.5


def _predicted_remove(p_remove: float) -> bool:
    return p_remove >= HARD_LABEL_THRESHOLD


def _gold_remove(label: int) -> bool:
    return label == REMOVE_LABEL


def _p_remove_from_output(output: object) -> float | None:
    if isinstance(output, JevRolloutOutput):
        return output.p_remove
    p_remove = getattr(output, "p_remove", None)
    return float(p_remove) if p_remove is not None else None


def count_hard_label_correct(evaluation: object | None) -> int:
    """Count hard-label matches at 0.5 for one subsample evaluation."""
    if evaluation is None:
        return 0
    trajectories = getattr(evaluation, "trajectories", None) or []
    outputs = getattr(evaluation, "outputs", None) or []
    correct = 0
    if trajectories:
        for trajectory in trajectories:
            if not isinstance(trajectory, JevTrajectory):
                continue
            if _predicted_remove(trajectory.p_remove) == _gold_remove(trajectory.label):
                correct += 1
        return correct
    for output in outputs:
        p_remove = _p_remove_from_output(output)
        if p_remove is None:
            continue
        label = getattr(output, "label", None)
        if label is None:
            continue
        if _predicted_remove(p_remove) == _gold_remove(int(label)):
            correct += 1
    return correct


class HardLabelMarginAcceptance:
    """AcceptanceCriterion: compare hard labels at 0.5 on reflection minibatch.

    should_accept when correct_after >= correct_before + ACCEPTANCE_MARGIN_CORRECT (2).
    Use proposal.eval_before / eval_after trajectories or outputs; do not sum soft adapter scores.
    Optional reject_reason(proposal, state) -> str for logging.
    """

    def should_accept(self, proposal: CandidateProposal, state: GEPAState) -> bool:
        correct_before = count_hard_label_correct(proposal.eval_before)
        correct_after = count_hard_label_correct(proposal.eval_after)
        return correct_after >= correct_before + ACCEPTANCE_MARGIN_CORRECT

    def reject_reason(self, proposal: CandidateProposal, state: GEPAState) -> str:
        correct_before = count_hard_label_correct(proposal.eval_before)
        correct_after = count_hard_label_correct(proposal.eval_after)
        return (
            f"hard_label_margin: before={correct_before} after={correct_after} "
            f"required_delta={ACCEPTANCE_MARGIN_CORRECT}"
        )
