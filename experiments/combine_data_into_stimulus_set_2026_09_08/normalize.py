"""Map one curated export onto the shared stimulus columns."""

from __future__ import annotations

import pandas as pd


def normalize_curated_frame(frame: pd.DataFrame, source) -> pd.DataFrame:
    """Return one source table with the shared 17-column schema."""
    raise NotImplementedError
