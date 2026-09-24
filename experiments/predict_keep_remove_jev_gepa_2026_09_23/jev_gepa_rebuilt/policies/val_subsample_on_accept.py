"""Validation subsample policy: score 100 val posts only when a proposal is accepted.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_val_subsample_policy.py -q

Post budget: each id returned from ``get_eval_batch`` is one Jev post scored toward
``max_metric_calls`` (adapter reports post counts, not HTTP batches). Rejected
proposals set ``state.adapter_state['proposal_rejected']`` and receive an empty
eval batch so the full 300-post val set is not scored.
"""

from __future__ import annotations

import random
from typing import Sequence

from gepa.core.data_loader import DataId, DataInst, DataLoader
from gepa.core.state import GEPAState, ProgramIdx

PROPOSAL_REJECTED_KEY = "proposal_rejected"


def sample_val_subsample_ids(
    all_ids: Sequence[DataId],
    subsample_size: int,
    gepa_seed: int,
    iteration: int,
) -> list[DataId]:
    """Deterministically sample ``subsample_size`` validation ids for one iteration."""
    if subsample_size <= 0:
        return []
    universe = list(all_ids)
    if not universe:
        return []
    rng = random.Random()
    rng.seed(gepa_seed + iteration * 1_000_003)
    if subsample_size >= len(universe):
        return universe
    return rng.sample(universe, subsample_size)


class ValSubsampleOnAcceptPolicy:
    """EvaluationPolicy that returns an empty eval batch on reject and 100 val ids on accept.

    On accept, sample VAL_SUBSAMPLE_SIZE ids with rng seeded by (GEPA_SEED, state.i).
    Implement get_eval_batch, get_best_program, get_valset_score consistent with
    FullEvaluationPolicy averaging over stored subsample scores only.
    """

    def __init__(self, *, subsample_size: int, gepa_seed: int) -> None:
        self._subsample_size = subsample_size
        self._gepa_seed = gepa_seed

    def get_eval_batch(
        self,
        loader: DataLoader[DataId, DataInst],
        state: GEPAState,
        target_program_idx: ProgramIdx | None = None,
    ) -> list[DataId]:
        if state.adapter_state.get(PROPOSAL_REJECTED_KEY, False):
            return []
        return sample_val_subsample_ids(
            loader.all_ids(),
            self._subsample_size,
            self._gepa_seed,
            state.i,
        )

    def get_best_program(self, state: GEPAState) -> ProgramIdx:
        best_idx, best_score, best_coverage = -1, float("-inf"), -1
        for program_idx, scores in enumerate(state.prog_candidate_val_subscores):
            coverage = len(scores)
            avg = sum(scores.values()) / coverage if coverage else float("-inf")
            if avg > best_score or (avg == best_score and coverage > best_coverage):
                best_score = avg
                best_idx = program_idx
                best_coverage = coverage
        return best_idx

    def get_valset_score(self, program_idx: ProgramIdx, state: GEPAState) -> float:
        return state.get_program_average_val_subset(program_idx)[0]
