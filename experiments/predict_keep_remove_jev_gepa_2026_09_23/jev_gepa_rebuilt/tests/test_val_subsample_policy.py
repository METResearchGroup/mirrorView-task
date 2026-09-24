"""Tests for ValSubsampleOnAcceptPolicy."""

from __future__ import annotations

from unittest.mock import MagicMock

from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.constants import GEPA_SEED, VAL_SUBSAMPLE_SIZE
from experiments.predict_keep_remove_jev_gepa_2026_09_23.jev_gepa_rebuilt.policies.val_subsample_on_accept import (
    ValSubsampleOnAcceptPolicy,
    sample_val_subsample_ids,
)


class _StringIdLoader:
    def __init__(self, ids: list[str]) -> None:
        self._ids = ids

    def all_ids(self) -> list[str]:
        return list(self._ids)

    def fetch(self, ids: list[str]) -> list[object]:
        return [object() for _ in ids]

    def __len__(self) -> int:
        return len(self._ids)


class TestValSubsampleOnAcceptPolicy:
    """Tests for ValSubsampleOnAcceptPolicy.get_eval_batch."""

    def test_rejected_proposal_returns_empty_batch(self) -> None:
        """Rejected proposals skip validation scoring."""
        policy = ValSubsampleOnAcceptPolicy(
            subsample_size=VAL_SUBSAMPLE_SIZE,
            gepa_seed=GEPA_SEED,
        )
        loader = _StringIdLoader([f"v{index}" for index in range(300)])
        state = MagicMock()
        state.i = 1
        state.adapter_state = {"proposal_rejected": True}
        result = policy.get_eval_batch(loader, state)
        assert result == []

    def test_accepted_iteration_samples_deterministic_hundred(self) -> None:
        """Accepted iteration draws a fixed 100-id subsample for seed and i."""
        policy = ValSubsampleOnAcceptPolicy(
            subsample_size=VAL_SUBSAMPLE_SIZE,
            gepa_seed=GEPA_SEED,
        )
        all_ids = [f"v{index}" for index in range(300)]
        loader = _StringIdLoader(all_ids)
        state = MagicMock()
        state.i = 3
        state.adapter_state = {"proposal_rejected": False}
        expected = sample_val_subsample_ids(all_ids, VAL_SUBSAMPLE_SIZE, GEPA_SEED, 3)
        result = policy.get_eval_batch(loader, state)
        assert len(result) == VAL_SUBSAMPLE_SIZE
        assert result == expected
