"""Tests for post-GEPA candidate selection on dev-A/dev-B."""

from __future__ import annotations

from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import (
    JevDataInst,
    JevRolloutOutput,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import STUDY_COMPONENT_KEY
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    TOP_ACCEPTED_CANDIDATES,
    VAL_DEV_GAP_MAX,
)
from unittest.mock import patch

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.selection import (
    filter_top10_val_dev_gap,
    preselect_top_by_val_score,
    select_on_dev_ab,
)


class _IdxProbabilityAdapter:
    """Returns p_remove fixed per candidate index for dev/val scoring."""

    def __init__(self, p_remove_by_idx: dict[int, float]) -> None:
        self._p_remove_by_idx = p_remove_by_idx
        self._current_idx = 0

    def set_candidate_idx(self, idx: int) -> None:
        self._current_idx = idx

    def evaluate(self, batch: list[JevDataInst], candidate: dict[str, str], capture_traces: bool = False):
        from gepa.core.adapter import EvaluationBatch

        p_remove = self._p_remove_by_idx.get(self._current_idx, 0.5)
        outputs = [JevRolloutOutput(post_id=inst.post_id, p_remove=p_remove) for inst in batch]
        return EvaluationBatch(outputs=outputs, scores=[0.0] * len(outputs), trajectories=None, num_metric_calls=len(batch))


def _inst(post_id: str, label: int) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text="a",
        mirror_text="b",
        post_1_role="original",
        post_2_role="mirror",
        label=label,
        n_keep=1,
        n_remove=0,
        n_raters=1,
        remove_share=0.0,
        sampled_stance="n",
        sample_toxicity_type="n",
    )


class TestPreselectTop10:
    """Tests for preselect_top_by_val_score."""

    def test_returns_highest_val_scores(self) -> None:
        """Top 10 accepted indices are those with highest val_aggregate_scores."""
        accepted = list(range(1, 16))
        val_scores = [float(idx) for idx in range(16)]
        result = GEPAResult(
            candidates=[{STUDY_COMPONENT_KEY: "seed"}] + [{STUDY_COMPONENT_KEY: f"c{i}"} for i in range(1, 16)],
            parents=[[None]] * 16,
            val_aggregate_scores=val_scores,
            val_subscores=[{}] * 16,
            per_val_instance_best_candidates={},
            discovery_eval_counts=[0] * 16,
            total_metric_calls=0,
        )
        top = preselect_top_by_val_score(result, accepted, k=TOP_ACCEPTED_CANDIDATES)
        assert top == list(range(15, 5, -1))


class TestFilterValDevGap:
    """Tests for filter_top10_val_dev_gap."""

    def test_drops_candidate_with_excessive_val_dev_gap(self) -> None:
        """Rejects when val balanced accuracy minus dev-A exceeds VAL_DEV_GAP_MAX."""
        adapter = _IdxProbabilityAdapter({0: 0.5, 1: 0.5})
        dev_a = [_inst("a1", 0), _inst("a2", 1)]
        val_instances = [_inst("v1", 0), _inst("v2", 1)]
        candidates = [{STUDY_COMPONENT_KEY: "c0"}, {STUDY_COMPONENT_KEY: "c1"}]
        val_subsample_ids_by_idx = {0: ["v1", "v2"], 1: ["v1", "v2"]}
        val_inst_by_post_id = {inst.post_id: inst for inst in val_instances}

        with patch(
            "experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.selection._balanced_accuracy_at_half",
            side_effect=[0.60, 0.85, 0.65, 0.70],
        ):
            filtered = filter_top10_val_dev_gap(
                adapter,
                [0, 1],
                candidates,
                dev_a,
                val_subsample_ids_by_idx=val_subsample_ids_by_idx,
                val_inst_by_post_id=val_inst_by_post_id,
                val_dev_gap_max=VAL_DEV_GAP_MAX,
            )
        assert filtered == [1]


class TestSelectOnDevAb:
    """Tests for select_on_dev_ab."""

    def test_threshold_from_dev_a_and_dev_b_at_same_threshold(self) -> None:
        """Threshold maximizes dev-A F1; dev-B F1 uses that same threshold."""
        adapter = _IdxProbabilityAdapter({0: 0.8, 1: 0.2})
        dev_a = [_inst("a1", 1), _inst("a2", 0)]
        dev_b = [_inst("b1", 1), _inst("b2", 0)]
        candidates = [{STUDY_COMPONENT_KEY: "c0"}, {STUDY_COMPONENT_KEY: "c1"}]

        selected_idx, threshold, dev_a_f1, dev_b_f1, rows = select_on_dev_ab(
            adapter,
            candidates,
            [0, 1],
            dev_a,
            dev_b,
        )
        assert selected_idx in (0, 1)
        assert 0.05 <= threshold <= 0.95
        assert dev_a_f1 >= 0.0
        assert dev_b_f1 >= 0.0
        assert len(rows) == 2
