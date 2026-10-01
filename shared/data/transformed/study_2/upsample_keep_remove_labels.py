"""Write balanced Study 2 keep/remove tables from the registered sources.

Run from repo root::

    PYTHONPATH=. uv run python shared/data/transformed/study_2/upsample_keep_remove_labels.py
"""

from __future__ import annotations

import pandas as pd

from shared.data import dataloader, registry
from shared.data.registry import (
    STUDY_2_KEEP_REMOVE_LABELS,
    STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)
from shared.utils.upsample import upsample_df

CLASS_LABEL_COLUMN = "keep_remove_label"

SOURCE_OUTPUT_PAIRS: tuple[tuple[str, str], ...] = (
    (STUDY_2_KEEP_REMOVE_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS),
    (STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS),
    (STUDY_2_KEEP_REMOVE_SPLIT_LABELS, UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS),
)


def write_upsampled_keep_remove_label_datasets() -> dict[str, pd.DataFrame]:
    """Load the three source tables, balance each one, and write its CSV.

    Returns
    -------
    dict[str, pandas.DataFrame]
        Balanced frames keyed by output registry name, in ``SOURCE_OUTPUT_PAIRS``
        order. Each CSV is written at that name's registry path with no index
        column.
    """
    # load → balance → resolve → write
    ...


def main() -> None:
    """Print one line per written table, in source pair order.

    Each line includes the output registry name, absolute local path, row
    count, and class counts sorted by class value.
    """
    write_upsampled_keep_remove_label_datasets()
    ...


if __name__ == "__main__":
    main()
