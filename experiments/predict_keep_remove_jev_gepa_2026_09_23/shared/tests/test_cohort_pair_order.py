"""Tests for deterministic pair order assignment."""

from __future__ import annotations

import pandas as pd

from experiments.predict_keep_remove_jev_gepa_2026_09_23.shared.cohort import (
    attach_pair_order,
    pair_order_for_post,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    PAIR_ORDER_SEED,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)

GOLDEN_POST_ID = "test_post"


class TestPairOrderForPost:
    def test_golden_case_at_seed_zero(self) -> None:
        assert pair_order_for_post(GOLDEN_POST_ID, seed=PAIR_ORDER_SEED) == (
            ROLE_ORIGINAL,
            ROLE_MIRROR,
        )


class TestAttachPairOrder:
    def test_fills_post_role_columns(self) -> None:
        cohort = pd.DataFrame({"post_id": [GOLDEN_POST_ID, "P1"]})
        result = attach_pair_order(cohort)

        assert result.loc[0, "post_1_role"] == ROLE_ORIGINAL
        assert result.loc[0, "post_2_role"] == ROLE_MIRROR
        assert result.loc[1, "post_1_role"] == ROLE_MIRROR
        assert result.loc[1, "post_2_role"] == ROLE_ORIGINAL
