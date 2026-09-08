"""Map one curated export onto the shared stimulus columns."""

from __future__ import annotations

import pandas as pd

from experiments.combine_data_into_stimulus_set_2026_09_08.sources import CuratedSource


def normalize_curated_frame(frame: pd.DataFrame, source: CuratedSource) -> pd.DataFrame:
    """Return one source table with the shared 17-column schema.

    Parameters
    ----------
    frame
        Curated export as downloaded.
    source
        Pinned identity used to fill platform and source columns.

    Returns
    -------
    pd.DataFrame
        Table with the shared combine columns in contract order.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    raise NotImplementedError
