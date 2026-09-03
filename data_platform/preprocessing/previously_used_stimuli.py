"""Skip preprocess candidates that were already used as study stimuli.

Study catalogs store each stimulus id as ``post_primary_key``. Ingest writes
the matching value on each raw row as ``record_id``. For Part 2 Reddit catalog
keys of the form ``reddit_{post_id}_{comment_id}``, the skip set also includes
the ingest form ``reddit_t1_{comment_id}``. The module loads those keys and
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
from data_platform.ingestion.generate_record_id import INTEGRATION_REDDIT
from data_platform.utils.platform_specific_columns import STANDARDIZED_RECORD_ID_COLUMN

STIMULI_ID_COLUMN = "post_primary_key"
STIMULI_DATASET_KIND: DatasetKind = "stimuli"
REDDIT_CATALOG_KEY_SEGMENT_COUNT = 3
REDDIT_COMMENT_FULLNAME_KIND = "t1"


def _reddit_ingest_aliases(stimuli_id: str) -> set[str]:
    """Return ingest ``record_id`` forms for a Part 2 Reddit catalog key.

    Catalog keys are ``reddit_{post_id}_{comment_id}``. Ingest writes
    ``reddit_t1_{comment_id}`` from ``comment_fullname``.
    """
    segments = stimuli_id.split("_")
    if len(segments) != REDDIT_CATALOG_KEY_SEGMENT_COUNT:
        return set()
    integration, _post_id, comment_id = segments
    if integration != INTEGRATION_REDDIT or not comment_id:
        return set()
    return {f"{INTEGRATION_REDDIT}_{REDDIT_COMMENT_FULLNAME_KIND}_{comment_id}"}


def extract_stimuli_ids(frame: pd.DataFrame, dataset_name: str) -> set[str]:
    """Return catalog ``post_primary_key`` values plus ingest-form aliases.

    Blank and missing cells are omitted. Part 2 Reddit keys also add the
    ``reddit_t1_{comment_id}`` ingest ``record_id``.

    Parameters
    ----------
    frame
        One registered stimuli CSV as a dataframe.
    dataset_name
        Registry name used in the missing-column error.

    Returns
    -------
    set[str]
        Catalog keys plus Reddit ingest aliases. Blank and missing cells
        are omitted.

    Raises
    ------
    ValueError
        When ``post_primary_key`` is missing from ``frame``.
    """
    if STIMULI_ID_COLUMN not in frame.columns:
        raise ValueError(f"{dataset_name}: missing {STIMULI_ID_COLUMN} column")
    keys = frame[STIMULI_ID_COLUMN].dropna().map(lambda value: str(value).strip())
    catalog_ids = {key for key in keys if key}
    ingest_ids = set(catalog_ids)
    for stimuli_id in catalog_ids:
        ingest_ids |= _reddit_ingest_aliases(stimuli_id)
    return ingest_ids


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
    ids: set[str] = set()
    for entry in datasets.values():
        if entry.kind != STIMULI_DATASET_KIND:
            continue
        frame = load_dataset(entry.name)
        ids |= extract_stimuli_ids(frame, entry.name)
    return ids


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
    if STANDARDIZED_RECORD_ID_COLUMN not in records.columns:
        raise KeyError(STANDARDIZED_RECORD_ID_COLUMN)
    if records.empty:
        return records.copy(), 0

    is_new = ~records[STANDARDIZED_RECORD_ID_COLUMN].map(str).isin(list(stimuli_ids))
    skipped = len(records) - int(is_new.sum())
    kept = records.loc[is_new].reset_index(drop=True)
    return kept, skipped
