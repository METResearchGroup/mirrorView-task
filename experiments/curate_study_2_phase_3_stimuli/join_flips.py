"""Inner-join posts to successful flips and count stance by toxicity cells."""

from __future__ import annotations

import pandas as pd

from experiments.curate_study_2_phase_3_stimuli.sources import JoinedFlipPool


def join_posts_to_flips(
    sample_posts: pd.DataFrame,
    sample_flips: pd.DataFrame,
    unified_posts: pd.DataFrame,
    unified_flips: pd.DataFrame,
) -> JoinedFlipPool:
    """Inner-join each post table to its flips and concatenate the two pieces.

    Toxicity comes from the original post table. The 300 promoted posts count
    as high.

    Raises
    ------
    ValueError
        When the same ``record_id`` appears in both joined pieces, or when
        original text does not match post text.
    """
    raise NotImplementedError


def available_cell_counts(pool: pd.DataFrame) -> dict[str, dict[str, int]]:
    """Return political stance by toxicity counts for posts that have a flip."""
    raise NotImplementedError


def cells_meet_targets(available: dict[str, dict[str, int]]) -> bool:
    """Return True when every stance by toxicity cell meets its catalog target."""
    raise NotImplementedError
