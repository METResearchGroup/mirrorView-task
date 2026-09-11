"""Tests for sample_mixed_feeds()."""

from __future__ import annotations

import pytest

from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow
from experiments.load_study_assignments_2026_09_09.split import parse_original_user_id
from experiments.upsample_mixed_study_feeds_2026_09_11.tests.conftest import (
    LEFTOVER_LEFT_USER_IDS,
    MIXED_USER_IDS,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.upsample import (
    sample_mixed_feeds,
    select_mixed_rows,
)


class TestSampleMixedFeeds:
    """Tests for sample_mixed_feeds()."""

    def test_seed_zero_is_deterministic_without_replacement(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
    ) -> None:
        """Verifies two draws with seed 0 return the same unique mixed ids."""
        mixed_rows = mixed_and_leftover_rows[:4]

        first = sample_mixed_feeds(mixed_rows, 2, 0)
        second = sample_mixed_feeds(mixed_rows, 2, 0)

        first_ids = [parse_original_user_id(row.id) for row in first]
        second_ids = [parse_original_user_id(row.id) for row in second]
        expected = first_ids
        result = second_ids
        assert result == expected
        assert len(set(result)) == 2
        assert set(result) <= set(MIXED_USER_IDS)

    def test_full_pool_sample_ids_are_unique(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
    ) -> None:
        """Verifies sampling the whole mixed pool never repeats a source id."""
        mixed_rows = mixed_and_leftover_rows[:4]
        expected = 4

        result = sample_mixed_feeds(mixed_rows, 4, 0)

        result_ids = [parse_original_user_id(row.id) for row in result]
        assert len(set(result_ids)) == expected

    def test_select_then_sample_excludes_leftover_left(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
        stance_by_post: dict[str, str],
    ) -> None:
        """Verifies leftover-left user ids are not sampled after mixed selection."""
        mixed_rows = select_mixed_rows(mixed_and_leftover_rows, stance_by_post)

        result = sample_mixed_feeds(mixed_rows, 2, 0)

        result_ids = {parse_original_user_id(row.id) for row in result}
        assert result_ids.isdisjoint(set(LEFTOVER_LEFT_USER_IDS))

    def test_raises_when_count_exceeds_pool(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
    ) -> None:
        """Verifies sampling 5 from 4 mixed rows raises ValueError."""
        mixed_rows = mixed_and_leftover_rows[:4]

        with pytest.raises(ValueError):
            sample_mixed_feeds(mixed_rows, 5, 0)

    def test_raises_when_count_is_zero(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
    ) -> None:
        """Verifies sampling 0 mixed rows raises ValueError."""
        mixed_rows = mixed_and_leftover_rows[:4]

        with pytest.raises(ValueError):
            sample_mixed_feeds(mixed_rows, 0, 0)
