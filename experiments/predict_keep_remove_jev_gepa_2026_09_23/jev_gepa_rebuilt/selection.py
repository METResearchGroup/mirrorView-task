"""Post-GEPA candidate preselection and dev-A/dev-B selection.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_selection_top10.py -q
"""

from __future__ import annotations

from typing import Mapping, Sequence

from gepa.core.result import GEPAResult

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevDataInst, JevGepaRebuiltAdapter
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    STUDY_COMPONENT_KEY,
    TOP_ACCEPTED_CANDIDATES,
    VAL_DEV_GAP_MAX,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.metrics import probability_metrics, tune_threshold_for_f1

HARD_LABEL_THRESHOLD = 0.5


def list_accepted_candidate_indices(
    result: GEPAResult,
    acceptance_log: Sequence[dict],
) -> list[int]:
    """Indices where proposal was accepted (exclude seed 0 if never accepted)."""
    accepted = {
        int(row["candidate_idx"])
        for row in acceptance_log
        if row.get("accepted") is True and "candidate_idx" in row
    }
    seed_accepted = any(
        int(row.get("candidate_idx", -1)) == 0 and row.get("accepted") is True for row in acceptance_log
    )
    if 0 not in accepted and not seed_accepted:
        accepted.discard(0)
    return sorted(accepted)


def preselect_top_by_val_score(
    result: GEPAResult,
    accepted_indices: list[int],
    *,
    k: int = TOP_ACCEPTED_CANDIDATES,
) -> list[int]:
    """Sort by result.val_aggregate_scores[idx] descending; tie-break lower idx."""
    ranked = sorted(
        accepted_indices,
        key=lambda idx: (-float(result.val_aggregate_scores[idx]), idx),
    )
    return ranked[:k]


def _balanced_accuracy_at_half(
    adapter: JevGepaRebuiltAdapter,
    candidate: dict[str, str],
    instances: list[JevDataInst],
) -> float:
    if not instances:
        return 0.0
    eval_batch = adapter.evaluate(instances, candidate, capture_traces=False)
    labels = [example.label for example in instances]
    probabilities = [output.p_remove for output in eval_batch.outputs]
    return probability_metrics(labels, probabilities, threshold=HARD_LABEL_THRESHOLD).balanced_accuracy


def filter_top10_val_dev_gap(
    adapter: JevGepaRebuiltAdapter,
    candidate_indices: list[int],
    candidates: list[dict[str, str]],
    dev_a: list[JevDataInst],
    *,
    val_subsample_ids_by_idx: Mapping[int, list[int]] | None,
    val_inst_by_post_id: Mapping[str, JevDataInst],
    val_dev_gap_max: float = VAL_DEV_GAP_MAX,
) -> list[int]:
    """For each idx, compare val subsample vs dev-A balanced accuracy at 0.5."""
    kept: list[int] = []
    for idx in candidate_indices:
        candidate = candidates[idx]
        dev_balanced = _balanced_accuracy_at_half(adapter, candidate, dev_a)
        val_instances: list[JevDataInst] = []
        if val_subsample_ids_by_idx is not None:
            for val_id in val_subsample_ids_by_idx.get(idx, []):
                key = str(val_id)
                if key in val_inst_by_post_id:
                    val_instances.append(val_inst_by_post_id[key])
        val_balanced = _balanced_accuracy_at_half(adapter, candidate, val_instances)
        if val_balanced - dev_balanced <= val_dev_gap_max:
            kept.append(idx)
    return kept


def select_on_dev_ab(
    adapter: JevGepaRebuiltAdapter,
    candidates: list[dict[str, str]],
    candidate_indices: list[int],
    dev_a: list[JevDataInst],
    dev_b: list[JevDataInst],
) -> tuple[int, float, float, float, list[dict]]:
    """Tune threshold on dev-A F1; return best candidate and per-row dev metrics."""
    best_idx = candidate_indices[0]
    best_dev_a_f1 = -1.0
    best_threshold = HARD_LABEL_THRESHOLD
    best_dev_b_f1 = 0.0
    rows: list[dict] = []

    for idx in candidate_indices:
        candidate = candidates[idx]
        dev_a_eval = adapter.evaluate(dev_a, candidate, capture_traces=False)
        dev_a_labels = [example.label for example in dev_a]
        dev_a_probs = [output.p_remove for output in dev_a_eval.outputs]
        threshold, dev_a_f1 = tune_threshold_for_f1(dev_a_labels, dev_a_probs)

        dev_b_eval = adapter.evaluate(dev_b, candidate, capture_traces=False)
        dev_b_labels = [example.label for example in dev_b]
        dev_b_probs = [output.p_remove for output in dev_b_eval.outputs]
        dev_b_f1 = probability_metrics(dev_b_labels, dev_b_probs, threshold=threshold).f1

        study_chars = len(candidate.get(STUDY_COMPONENT_KEY, ""))
        rows.append(
            {
                "candidate_idx": idx,
                "val_score": None,
                "dev_a_f1": dev_a_f1,
                "dev_b_f1": dev_b_f1,
                "threshold": threshold,
                "study_instruction_chars": study_chars,
                "accepted": True,
                "last_reject_reason": None,
            }
        )
        if dev_a_f1 > best_dev_a_f1:
            best_dev_a_f1 = dev_a_f1
            best_idx = idx
            best_threshold = threshold
            best_dev_b_f1 = dev_b_f1

    return best_idx, best_threshold, best_dev_a_f1, best_dev_b_f1, rows
