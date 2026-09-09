"""Shared fixtures for study user assignment tests."""

from __future__ import annotations

import pandas as pd
import pytest

from experiments.generate_study_user_assignments_2026_09_08.constants import (
    CELL_COLUMN,
    POST_ID_COLUMN,
    REMAINING_COUNT_COLUMN,
    STANCE_COLUMN,
    STANCE_LEFT,
    STANCE_RIGHT,
    TOXICITY_COLUMN,
    TOXICITY_HIGH,
    TOXICITY_LOW,
    TOXICITY_MIDDLE,
)

TOXICITY_BY_CELL = {
    1: TOXICITY_LOW,
    2: TOXICITY_MIDDLE,
    3: TOXICITY_HIGH,
    4: TOXICITY_LOW,
    5: TOXICITY_MIDDLE,
    6: TOXICITY_HIGH,
}
STANCE_BY_CELL = {
    1: STANCE_LEFT,
    2: STANCE_LEFT,
    3: STANCE_LEFT,
    4: STANCE_RIGHT,
    5: STANCE_RIGHT,
    6: STANCE_RIGHT,
}


def joined_posts_frame(posts_per_cell: dict[int, int], remaining_each: int) -> pd.DataFrame:
    """Build a joined remaining table with unique posts per cell.

    Parameters
    ----------
    posts_per_cell
        Cell number to unique post count.
    remaining_each
        Remaining labels on every post.
    """
    rows = []
    for cell, post_count in sorted(posts_per_cell.items()):
        stance = STANCE_BY_CELL[cell]
        toxicity = TOXICITY_BY_CELL[cell]
        for index in range(post_count):
            rows.append(
                {
                    POST_ID_COLUMN: f"p{cell}-{index:04d}",
                    STANCE_COLUMN: stance,
                    TOXICITY_COLUMN: toxicity,
                    REMAINING_COUNT_COLUMN: remaining_each,
                    CELL_COLUMN: cell,
                }
            )
    return pd.DataFrame(rows)


@pytest.fixture
def recipe_joined_frame() -> pd.DataFrame:
    """Enough unique remaining=1 posts to hit preferred recipes for two of each feed kind."""
    return joined_posts_frame(
        {1: 15, 2: 30, 3: 15, 4: 5, 5: 10, 6: 5}, remaining_each=1
    )


@pytest.fixture
def leftover_left_joined_frame() -> pd.DataFrame:
    """21 left remaining and 10 right remaining, unique posts with remaining 1."""
    return joined_posts_frame({1: 21, 4: 10}, remaining_each=1)


@pytest.fixture
def steal_joined_frame() -> pd.DataFrame:
    """Left-high remaining is 0. Other left cells still have remaining."""
    return joined_posts_frame({1: 20, 2: 20, 3: 0, 4: 4, 5: 10, 6: 6}, remaining_each=1)
