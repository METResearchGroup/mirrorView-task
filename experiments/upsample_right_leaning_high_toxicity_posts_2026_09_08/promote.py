"""Promote the top 300 scored right-medium posts to high and concatenate the unified table."""

from __future__ import annotations

import pandas as pd

from experiments.upsample_right_leaning_high_toxicity_posts_2026_09_08.sources import (
    PromotionResult,
)


def promote_top_candidates(
    candidates: pd.DataFrame,
    scores: pd.DataFrame,
    medium_upsample: pd.DataFrame,
) -> PromotionResult:
    """Reclassify the top 300 scored rows as high and concatenate the 2,000 medium posts.

    Parameters
    ----------
    candidates
        Leftover right-medium rows.
    scores
        ``record_id`` and ``toxicity_prob`` for those rows.
    medium_upsample
        The 2,000 unused medium posts. Toxicity stays medium.

    Returns
    -------
    PromotionResult
        Promoted rows and the unified 2,300 post table.

    Raises
    ------
    ValueError
        When a promotion is not right, still medium after the copy, or overlaps
        the 2,000 medium upsample.
    """
    raise NotImplementedError
