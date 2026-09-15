"""Tests for pair_order_for_post()."""

from __future__ import annotations

from experiments.reasoning_during_moderation_2026_09_15.shared.cohort import (
    pair_order_for_post,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    PAIR_ORDER_MIRROR_FIRST,
    PAIR_ORDER_ORIGINAL_FIRST,
    PAIR_ORDER_SEED,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)


class TestPairOrderForPost:
    """Tests for pair_order_for_post function."""

    def test_seed_zero_is_stable_for_one_post(self) -> None:
        """Verifies the same post id always returns the same order."""
        first = pair_order_for_post("A", PAIR_ORDER_SEED)
        second = pair_order_for_post("A", PAIR_ORDER_SEED)
        expected_roles = {ROLE_ORIGINAL, ROLE_MIRROR}

        assert first == second
        assert set(first) == expected_roles

    def test_both_orders_appear_across_posts(self) -> None:
        """Verifies twenty post ids include both pair orders."""
        orders = {pair_order_for_post(str(index), PAIR_ORDER_SEED) for index in range(20)}
        expected = {PAIR_ORDER_ORIGINAL_FIRST, PAIR_ORDER_MIRROR_FIRST}

        assert expected.issubset(orders)
