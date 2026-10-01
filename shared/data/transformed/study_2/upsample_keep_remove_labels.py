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
    return {
        output_name: _write_balanced_dataset(source_name, output_name)
        for source_name, output_name in SOURCE_OUTPUT_PAIRS
    }


def _write_balanced_dataset(source_name: str, output_name: str) -> pd.DataFrame:
    """Load one source, balance ``keep_remove_label``, and write its CSV."""
    source = dataloader.load_dataset(source_name, low_memory=False)
    balanced = upsample_df(source, CLASS_LABEL_COLUMN)
    output_path = registry.resolve_path(output_name)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    balanced.to_csv(output_path, index=False)
    return balanced


def main() -> None:
    """Print one line per written table, in source pair order.

    Each line includes the output registry name, absolute local path, row
    count, and class counts sorted by class value.
    """
    for output_name, frame in write_upsampled_keep_remove_label_datasets().items():
        _print_written_dataset(output_name, frame)


def _print_written_dataset(output_name: str, frame: pd.DataFrame) -> None:
    """Print the registry name, absolute path, row count, and class counts."""
    path = registry.resolve_path(output_name).resolve()
    counts = frame[CLASS_LABEL_COLUMN].value_counts().sort_index().to_dict()
    print(f"{output_name} path={path} rows={len(frame)} class_counts={counts}")


if __name__ == "__main__":
    main()
