"""Tests for party split append order and require_original_party_prefix()."""

from __future__ import annotations

from dataclasses import replace

import pytest

from experiments.load_study_assignments_2026_09_09.constants import (
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.split_batch import (
    require_original_party_prefix,
    split_rewritten,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.tests.conftest import (
    MIXED_POST_IDS,
    source_row,
)


class TestAppendPartyRows:
    """Tests for split_rewritten() and require_original_party_prefix()."""

    def test_clones_are_last_in_each_party_list(self) -> None:
        """Verifies original user 1 keeps Democrat index 0001 and clones are last."""
        rows = [source_row(user_id, MIXED_POST_IDS) for user_id in range(1, 5)]
        expected_democrat_ids = [
            "democrat-training_assisted-0001",
            "democrat-training_assisted-0002",
        ]
        expected_republican_ids = [
            "republican-training_assisted-0001",
            "republican-training_assisted-0002",
        ]
        expected_first_posts = source_row(1, MIXED_POST_IDS).assigned_post_ids

        result_democrat, result_republican = split_rewritten(rows)

        assert [row.id for row in result_democrat] == expected_democrat_ids
        assert [row.id for row in result_republican] == expected_republican_ids
        assert result_democrat[0].assigned_post_ids == expected_first_posts
        assert result_democrat[-1].assigned_post_ids == rows[2].assigned_post_ids
        assert result_republican[-1].assigned_post_ids == rows[3].assigned_post_ids

    def test_require_original_party_prefix_raises_on_mismatch(self) -> None:
        """Verifies a rewritten Democrat prefix mismatch raises ValueError."""
        original_rows = [
            source_row(user_id, MIXED_POST_IDS) for user_id in range(1, 3)
        ]
        expanded_rows = [
            source_row(user_id, MIXED_POST_IDS) for user_id in range(1, 5)
        ]
        original_democrat, original_republican = split_rewritten(original_rows)
        democrat, republican = split_rewritten(expanded_rows)
        mismatched = replace(
            democrat[0],
            assigned_post_ids="[]",
        )
        result_democrat = [mismatched, *democrat[1:]]

        with pytest.raises(ValueError):
            require_original_party_prefix(
                result_democrat,
                republican,
                original_democrat,
                original_republican,
            )
