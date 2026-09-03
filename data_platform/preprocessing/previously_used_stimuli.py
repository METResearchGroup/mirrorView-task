"""Skip preprocess candidates that were already used as study stimuli.

Study catalogs store those keys as ``post_primary_key``. Ingest writes the same
value on each raw row as ``record_id``. This module loads the catalog keys and
drops matching preprocess candidates.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.preprocessing.previously_used_stimuli import load_previously_used_stimuli_ids"
"""

from __future__ import annotations

from collections.abc import Mapping

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import DatasetEntry, DatasetKind

STIMULI_ID_COLUMN = "post_primary_key"
STIMULI_DATASET_KIND: DatasetKind = "stimuli"


def extract_stimuli_ids(frame: pd.DataFrame, dataset_name: str) -> set[str]:
    """Return non-empty ``post_primary_key`` values from one stimuli table.

    Parameters
    ----------
    frame
        One registered stimuli CSV as a dataframe.
    dataset_name
        Registry name used in the missing-column error.

    Returns
    -------
    set[str]
        Distinct stimuli ids. Blank and missing cells are omitted.

    Raises
    ------
    ValueError
        When ``post_primary_key`` is missing from ``frame``.
    """
    if STIMULI_ID_COLUMN not in frame.columns:
        raise ValueError(f"{dataset_name}: missing {STIMULI_ID_COLUMN} column")
    keys = frame[STIMULI_ID_COLUMN].dropna().map(lambda value: str(value).strip())
    return {key for key in keys if key}


def load_previously_used_stimuli_ids(
    datasets: Mapping[str, DatasetEntry],
) -> set[str]:
    """Load ``post_primary_key`` values from every registry stimuli dataset.

    Parameters
    ----------
    datasets
        The study dataset catalog. Only entries whose kind is ``stimuli``
        are read.

    Returns
    -------
    set[str]
        Union of stimuli ids across those tables.

    Raises
    ------
    FileNotFoundError
        When a registered stimuli CSV is missing on disk.
    ValueError
        When a stimuli table is missing ``post_primary_key``.
    """
    raise NotImplementedError


def filter_previously_used_stimuli(
    records: pd.DataFrame,
    stimuli_ids: set[str],
) -> tuple[pd.DataFrame, int]:
    """Drop rows whose ``record_id`` was already used as study stimuli.

    The input frame is not modified.

    Parameters
    ----------
    records
        Preprocess candidates. Must include ``record_id``.
    stimuli_ids
        Previously used study stimuli keys.

    Returns
    -------
    tuple[pd.DataFrame, int]
        Surviving rows with a reset index, then the number of dropped rows.

    Raises
    ------
    KeyError
        When ``record_id`` is missing from ``records``.
    """
    raise NotImplementedError
