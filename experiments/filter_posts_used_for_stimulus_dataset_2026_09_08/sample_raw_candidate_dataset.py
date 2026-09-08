"""Sample up to 1700 posts in each political stance by toxicity cell."""

from __future__ import annotations

import pandas as pd


def sample_raw_candidate_dataset(cleaned: pd.DataFrame) -> pd.DataFrame:
    """Return the sampled table with up to TARGET_PER_CELL rows per cell."""
    raise NotImplementedError
