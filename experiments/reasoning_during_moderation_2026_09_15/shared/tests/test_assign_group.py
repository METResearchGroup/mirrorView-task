"""Tests for assign_group() and build_cohort()."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.reasoning_during_moderation_2026_09_15.shared.cohort import (
    assign_group,
    build_cohort,
    drop_conflicting_worker_posts,
    dedupe_worker_post,
    slim_trials,
)
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    GROUP_SPLIT,
    GROUP_UNANIMOUS_KEEP,
    GROUP_UNANIMOUS_REMOVE,
    ROLE_MIRROR,
    ROLE_ORIGINAL,
)


class TestAssignGroup:
    """Tests for assign_group function."""

    @pytest.mark.parametrize(
        ("keep_count", "remove_count", "expected"),
        [
            (2, 2, GROUP_SPLIT),
            (3, 2, GROUP_SPLIT),
            (2, 3, GROUP_SPLIT),
            (4, 0, GROUP_UNANIMOUS_KEEP),
            (0, 4, GROUP_UNANIMOUS_REMOVE),
            (4, 1, None),
            (3, 0, None),
        ],
    )
    def test_vote_patterns(
        self, keep_count: int, remove_count: int, expected: str | None
    ) -> None:
        """Verifies split, unanimous, and excluded vote patterns."""
        result = assign_group(keep_count, remove_count)

        assert result == expected


class TestBuildCohort:
    """Tests for build_cohort function."""

    def test_keeps_eligible_posts_and_pair_roles(
        self, mixed_trials: pd.DataFrame
    ) -> None:
        """Verifies posts A-E remain and F and G drop, with distinct pair roles."""
        cleaned = dedupe_worker_post(drop_conflicting_worker_posts(slim_trials(mixed_trials)))
        result = build_cohort(cleaned)
        expected_posts = {"A", "B", "C", "D", "E"}

        assert set(result["post_id"].astype(str)) == expected_posts
        assert "F" not in set(result["post_id"].astype(str))
        assert "G" not in set(result["post_id"].astype(str))
        roles = {ROLE_ORIGINAL, ROLE_MIRROR}
        for _, row in result.iterrows():
            assert {row["post_1_role"], row["post_2_role"]} == roles
