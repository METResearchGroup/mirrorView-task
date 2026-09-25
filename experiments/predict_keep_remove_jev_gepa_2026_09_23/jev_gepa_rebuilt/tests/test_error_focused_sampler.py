"""Tests for ErrorFocusedBatchSampler."""

from __future__ import annotations

from unittest.mock import MagicMock

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.adapter import JevDataInst
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import (
    GEPA_SEED,
    REFLECTION_MINIBATCH_SIZE,
)
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.error_focused_sampler import (
    ErrorFocusedBatchSampler,
)


def _inst(post_id: str, n_keep: int = 8, n_remove: int = 2) -> JevDataInst:
    return JevDataInst(
        post_id=post_id,
        original_text="o",
        mirror_text="m",
        post_1_role="original",
        post_2_role="mirror",
        label=0,
        n_keep=n_keep,
        n_remove=n_remove,
        n_raters=10,
        remove_share=n_remove / (n_keep + n_remove),
        sampled_stance="left",
        sample_toxicity_type="low",
    )


class _PostIdLoader:
    def __init__(self, instances: list[JevDataInst]) -> None:
        self._by_id = {instance.post_id: instance for instance in instances}

    def all_ids(self) -> list[str]:
        return list(self._by_id.keys())

    def fetch(self, ids: list[str]) -> list[JevDataInst]:
        return [self._by_id[post_id] for post_id in ids]

    def __len__(self) -> int:
        return len(self._by_id)


class TestErrorFocusedBatchSampler:
    """Tests for ErrorFocusedBatchSampler.next_minibatch_ids."""

    def test_misclassified_id_sampled_more_often(self) -> None:
        """Misclassified train ids appear more often than a random control id."""
        instances = [_inst(f"p{index}") for index in range(50)]
        loader = _PostIdLoader(instances)
        sampler = ErrorFocusedBatchSampler(
            minibatch_size=REFLECTION_MINIBATCH_SIZE,
            gepa_seed=GEPA_SEED,
            misclassified_ids={"p0"},
        )
        state = MagicMock()
        counts: dict[str, int] = {}
        for iteration in range(10):
            state.i = iteration
            batch = sampler.next_minibatch_ids(loader, state)
            assert len(batch) == REFLECTION_MINIBATCH_SIZE
            for post_id in batch:
                counts[post_id] = counts.get(post_id, 0) + 1
        assert counts.get("p0", 0) > counts.get("p25", 0)
