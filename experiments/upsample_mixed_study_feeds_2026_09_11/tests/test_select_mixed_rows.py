"""Tests for select_mixed_rows()."""

from __future__ import annotations

import pytest

from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow
from experiments.load_study_assignments_2026_09_09.split import parse_original_user_id
from experiments.upsample_mixed_study_feeds_2026_09_11.tests.conftest import (
    ELEVEN_NINE_POST_IDS,
    LEFTOVER_LEFT_USER_IDS,
    source_row,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.upsample import select_mixed_rows


class TestSelectMixedRows:
    """Tests for select_mixed_rows()."""

    def test_keeps_mixed_rows_and_drops_leftover_left(
        self,
        mixed_and_leftover_rows: list[AssignmentRow],
        stance_by_post: dict[str, str],
    ) -> None:
        """Verifies four mixed rows remain and leftover-left user ids are absent."""
        expected = 4

        result = select_mixed_rows(mixed_and_leftover_rows, stance_by_post)

        assert len(result) == expected
        result_user_ids = {parse_original_user_id(row.id) for row in result}
        assert result_user_ids.isdisjoint(set(LEFTOVER_LEFT_USER_IDS))

    def test_raises_for_eleven_left_nine_right(
        self, stance_by_post: dict[str, str]
    ) -> None:
        """Verifies an 11 left and 9 right feed raises ValueError."""
        rows = [source_row(1, ELEVEN_NINE_POST_IDS)]

        with pytest.raises(ValueError):
            select_mixed_rows(rows, stance_by_post)
