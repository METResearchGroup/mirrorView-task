"""Tests for join_remaining_to_catalogs()."""

import pandas as pd
import pytest

from experiments.generate_study_user_assignments_2026_09_08.constants import (
    CELL_COLUMN,
    POST_ID_COLUMN,
    REMAINING_BATCH_COLUMN,
    REMAINING_COUNT_COLUMN,
    REMAINING_ID_COLUMN,
    STANCE_COLUMN,
    STANCE_LEFT,
    TOXICITY_COLUMN,
    TOXICITY_MIDDLE,
)
from experiments.generate_study_user_assignments_2026_09_08.load import (
    join_remaining_to_catalogs,
)


def _remaining_row(post_id: str) -> dict[str, object]:
    return {
        REMAINING_ID_COLUMN: post_id,
        REMAINING_COUNT_COLUMN: 5,
        REMAINING_BATCH_COLUMN: "old",
    }


def _catalog_row(post_id: str, stance: str, toxicity: str) -> dict[str, str]:
    return {
        POST_ID_COLUMN: post_id,
        STANCE_COLUMN: stance,
        TOXICITY_COLUMN: toxicity,
    }


class TestJoinRemainingToCatalogs:
    """Tests for join_remaining_to_catalogs()."""

    def test_raises_when_id_is_in_neither_catalog(self) -> None:
        """Verifies a remaining id missing from both catalogs is rejected."""
        remaining = pd.DataFrame([_remaining_row("missing")])
        old_catalog = pd.DataFrame(
            [_catalog_row("old-1", STANCE_LEFT, TOXICITY_MIDDLE)]
        )
        new_catalog = pd.DataFrame(
            [_catalog_row("new-1", STANCE_LEFT, TOXICITY_MIDDLE)]
        )

        with pytest.raises(ValueError):
            join_remaining_to_catalogs(remaining, old_catalog, new_catalog)

    def test_raises_when_id_is_in_both_catalogs(self) -> None:
        """Verifies a remaining id present in both catalogs is rejected."""
        remaining = pd.DataFrame([_remaining_row("shared")])
        catalog_row = _catalog_row("shared", STANCE_LEFT, TOXICITY_MIDDLE)
        old_catalog = pd.DataFrame([catalog_row])
        new_catalog = pd.DataFrame([catalog_row])

        with pytest.raises(ValueError):
            join_remaining_to_catalogs(remaining, old_catalog, new_catalog)

    def test_maps_left_middle_toxicity_to_cell_2(self) -> None:
        """Verifies left middle-toxicity rows map to cell 2."""
        remaining = pd.DataFrame([_remaining_row("left-mid")])
        old_catalog = pd.DataFrame(
            [_catalog_row("left-mid", STANCE_LEFT, TOXICITY_MIDDLE)]
        )
        new_catalog = pd.DataFrame(
            columns=[POST_ID_COLUMN, STANCE_COLUMN, TOXICITY_COLUMN]
        )

        result = join_remaining_to_catalogs(remaining, old_catalog, new_catalog)

        assert result.loc[0, CELL_COLUMN] == 2
        assert result.loc[0, POST_ID_COLUMN] == "left-mid"
