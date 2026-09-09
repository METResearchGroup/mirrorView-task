"""Sample leftover left-medium and right-medium posts after dropping the 10,200 sample."""

from __future__ import annotations

import pandas as pd

def sample_leftover_medium(
    cleaned: pd.DataFrame,
    sample: pd.DataFrame,
) -> tuple[pd.DataFrame, int, int]:
    """Return 1,000 leftover left-medium and 1,000 leftover right-medium posts.

    Parameters
    ----------
    cleaned
        Cleaned combined table.
    sample
        The 10,200 post sample whose ids must be dropped.

    Returns
    -------
    tuple[pd.DataFrame, int, int]
        Sampled rows, leftover left-medium count, leftover right-medium count.

    Raises
    ------
    ValueError
        When either leftover medium cell has fewer than 1,000 rows.
    """
    raise NotImplementedError
