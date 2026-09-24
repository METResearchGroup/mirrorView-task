"""Tests for joint-model role shares."""

from __future__ import annotations

import pandas as pd

from experiments.bertopic_original_mirror_part3_2026_09_24.src.analyze_cross_role import (
    flag_role_dominated,
    pair_coassignment_rate,
    role_share_table,
)


class TestRoleShare:
    """Tests for role_share_table and flag_role_dominated."""

    def test_original_share_0_5_when_balanced(self) -> None:
        """Equal original and mirror rows give share 0.5."""
        assignments = pd.DataFrame(
            {
                "post_id": ["a", "a", "b", "b"],
                "text_role": ["original", "mirror", "original", "mirror"],
                "topic": [0, 0, 0, 0],
            }
        )

        result = role_share_table(assignments)

        assert float(result.loc[0, "original_share"]) == 0.5

    def test_role_dominated_flag_requires_q_below_0_05_and_share_outside_band(self) -> None:
        """A lopsided share is flagged only when the q-value is below 0.05."""
        assert flag_role_dominated(original_share=0.9, q_value_bh=0.01) is True
        assert flag_role_dominated(original_share=0.9, q_value_bh=0.10) is False


class TestPairCoassignment:
    """Tests for pair_coassignment_rate."""

    def test_coassignment_rate_one_when_same_topic(self) -> None:
        """Every pair sharing a topic yields rate 1."""
        assignments = pd.DataFrame(
            {
                "post_id": ["a", "a"],
                "text_role": ["original", "mirror"],
                "topic": [4, 4],
            }
        )

        result = pair_coassignment_rate(assignments)

        assert result["pair_coassignment_rate"] == 1.0
