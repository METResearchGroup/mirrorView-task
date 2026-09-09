"""Sample leftover left-medium and right-medium posts after dropping the 10,200 sample."""

from __future__ import annotations

import pandas as pd

from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    LeftoverMediumSample,
)


def sample_leftover_medium(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
) -> LeftoverMediumSample:
    """Return 1,000 leftover left-medium and 1,000 leftover right-medium posts.

    Parameters
    ----------
    cleaned
        Cleaned combined table.
    sample
        The 10,200 post sample whose ids must be dropped.

    Returns
    -------
    LeftoverMediumSample
        Sampled rows plus leftover medium counts before sampling.

    Raises
    ------
    ValueError
        When either leftover medium cell has fewer than 1,000 rows.
    """
    raise NotImplementedError
