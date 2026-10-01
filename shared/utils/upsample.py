"""Balance a DataFrame so each class has as many rows as the largest class.

Run from repo root::

    PYTHONPATH=. uv run python -c "from shared.utils.upsample import upsample_df"
"""

from __future__ import annotations

import pandas as pd


def upsample_df(
    df: pd.DataFrame,
    class_label: str,
    *,
    random_state: int = 1,
) -> pd.DataFrame:
    ...
