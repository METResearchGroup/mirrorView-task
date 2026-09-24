"""Error-focused train minibatch sampler for reflection.

Run from the repo root:

    PYTHONPATH=. uv run pytest experiments/predict_keep_remove_jev_gepa_2026_09_23/jev_gepa_rebuilt/tests/test_error_focused_sampler.py -q

Priority order: misclassifications from the last eval, confident errors, close vote
splits (``abs(n_keep - n_remove) <= 1``), contrastive opposites, then epoch shuffle.
Each ``next_minibatch_ids`` call returns REFLECTION_MINIBATCH_SIZE ids (25 posts).
"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence

from gepa.core.adapter import DataInst
from gepa.core.data_loader import DataId, DataLoader
from gepa.core.state import GEPAState
from gepa.strategies.batch_sampler import EpochShuffledBatchSampler

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevDataInst

CLOSE_VOTE_MARGIN = 1


class ErrorFocusedBatchSampler:
    """BatchSampler preferring misclassified train ids, confident errors, close vote splits.

    Maintain epoch_shuffled fallback. Accept optional indexes: misclassified set,
    confident_error set, contrastive partner map (may be empty until Step 4 builds index).
    next_minibatch_ids returns REFLECTION_MINIBATCH_SIZE ids.
    """

    def __init__(
        self,
        *,
        minibatch_size: int,
        gepa_seed: int,
        misclassified_ids: Sequence[DataId] | None = None,
        confident_error_ids: Sequence[DataId] | None = None,
        contrastive_partner_map: Mapping[DataId, DataId] | None = None,
    ) -> None:
        self.minibatch_size = minibatch_size
        self._rng = random.Random(gepa_seed)
        self.misclassified_ids: set[DataId] = set(misclassified_ids or ())
        self.confident_error_ids: set[DataId] = set(confident_error_ids or ())
        self.contrastive_partner_map: dict[DataId, DataId] = dict(contrastive_partner_map or {})
        self._fallback = EpochShuffledBatchSampler(minibatch_size, rng=random.Random(gepa_seed + 1))
        self._priority_cursor = 0

    def _close_vote_ids(self, loader: DataLoader[DataId, DataInst]) -> list[DataId]:
        close_vote: list[DataId] = []
        for post_id in loader.all_ids():
            batch = loader.fetch([post_id])
            if not batch:
                continue
            instance = batch[0]
            if isinstance(instance, JevDataInst):
                if abs(instance.n_keep - instance.n_remove) <= CLOSE_VOTE_MARGIN:
                    close_vote.append(post_id)
        return close_vote

    def _priority_pool(self, loader: DataLoader[DataId, DataInst]) -> list[DataId]:
        pool: list[DataId] = []
        for post_id in self.misclassified_ids:
            if post_id in loader.all_ids():
                pool.append(post_id)
        for post_id in self.confident_error_ids:
            if post_id in loader.all_ids() and post_id not in pool:
                pool.append(post_id)
        for post_id in self._close_vote_ids(loader):
            if post_id not in pool:
                pool.append(post_id)
        for post_id in self.contrastive_partner_map:
            if post_id in loader.all_ids() and post_id not in pool:
                pool.append(post_id)
            partner = self.contrastive_partner_map[post_id]
            if partner in loader.all_ids() and partner not in pool:
                pool.append(partner)
        return pool

    def _fill_from_priority_pool(self, pool: list[DataId]) -> list[DataId]:
        if not pool:
            return []
        ordered = list(pool)
        self._rng.shuffle(ordered)
        start = self._priority_cursor % len(ordered)
        self._priority_cursor += 1
        rotated = ordered[start:] + ordered[:start]
        chosen: list[DataId] = []
        index = 0
        while len(chosen) < self.minibatch_size:
            chosen.append(rotated[index % len(rotated)])
            index += 1
        return chosen

    def next_minibatch_ids(self, loader: DataLoader[DataId, DataInst], state: GEPAState) -> list[DataId]:
        pool = self._priority_pool(loader)
        if pool:
            return self._fill_from_priority_pool(pool)
        return self._fallback.next_minibatch_ids(loader, state)
