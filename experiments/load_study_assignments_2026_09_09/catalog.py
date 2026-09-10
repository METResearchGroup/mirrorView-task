"""Union the June catalog and the pull request 273 catalog for assigned posts.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    pinned_new_catalog,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.load import (
    load_new_catalog,
)
from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CATALOG_COLUMNS,
    EMPTY_CELL,
    MIRROR_TEXT_COLUMN,
    NAN_CELL,
    OLD_STIMULI_DATASET,
    ORIGINAL_TEXT_COLUMN,
    POST_ID_COLUMN,
    STANCE_COLUMN,
)
from experiments.load_study_assignments_2026_09_09.split import parse_post_ids
from shared.data.dataloader import load_dataset


def load_old_catalog_rows() -> pd.DataFrame:
    """Load the June stimulus catalog with the five catalog columns.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    return _catalog_columns(load_dataset(OLD_STIMULI_DATASET))


def load_new_catalog_rows(
    store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    """Download the pinned pull request 273 catalog and return catalog columns.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or required columns do not match.
    """
    return _catalog_columns(load_new_catalog(pinned_new_catalog(), store, cache_dir))


def union_catalogs(
    old_catalog: pd.DataFrame, new_catalog: pd.DataFrame
) -> pd.DataFrame:
    """Concatenate catalogs after rejecting overlapping post ids.

    Raises
    ------
    ValueError
        When a required column is missing or a post id appears in both catalogs.
    """
    _require_columns(old_catalog, CATALOG_COLUMNS)
    _require_columns(new_catalog, CATALOG_COLUMNS)
    _reject_duplicate_keys(old_catalog, new_catalog)
    return pd.concat([old_catalog, new_catalog], ignore_index=True)


def build_assigned_catalog(
    old_catalog: pd.DataFrame,
    new_catalog: pd.DataFrame,
    rows: list[AssignmentRow],
) -> pd.DataFrame:
    """Return assigned catalog rows, sorted by post id.

    Raises
    ------
    ValueError
        When an assigned id is missing, duplicated across catalogs, or
        missing original or mirror text.
    """
    union = union_catalogs(old_catalog, new_catalog)
    selected = _rows_for_ids(union, collect_assigned_ids(rows))
    _require_assigned_text(selected)
    return selected.sort_values(POST_ID_COLUMN).reset_index(drop=True)


def collect_assigned_ids(rows: list[AssignmentRow]) -> set[str]:
    """Return every post id from every rewritten assignment row."""
    return {
        post_id
        for row in rows
        for post_id in parse_post_ids(row.assigned_post_ids)
    }


def stance_by_id(catalog: pd.DataFrame) -> dict[str, str]:
    """Return ``post_primary_key`` to ``sampled_stance``."""
    return dict(
        zip(
            catalog[POST_ID_COLUMN].astype(str),
            catalog[STANCE_COLUMN].astype(str),
        )
    )


def _catalog_columns(catalog: pd.DataFrame) -> pd.DataFrame:
    _require_columns(catalog, CATALOG_COLUMNS)
    return catalog.loc[:, list(CATALOG_COLUMNS)].copy()


def _reject_duplicate_keys(
    old_catalog: pd.DataFrame, new_catalog: pd.DataFrame
) -> None:
    overlap = set(_id_values(old_catalog)) & set(_id_values(new_catalog))
    if overlap:
        raise ValueError(f"duplicate catalog id {sorted(overlap)[0]}")


def _rows_for_ids(union: pd.DataFrame, assigned_ids: set[str]) -> pd.DataFrame:
    selected = union.loc[union[POST_ID_COLUMN].astype(str).isin(assigned_ids)].copy()
    missing = assigned_ids - set(_id_values(selected))
    if missing:
        raise ValueError(f"missing catalog id {sorted(missing)[0]}")
    return selected


def _require_assigned_text(catalog: pd.DataFrame) -> None:
    for column in (ORIGINAL_TEXT_COLUMN, MIRROR_TEXT_COLUMN):
        if _empty_text_mask(catalog[column]).any():
            raise ValueError(f"empty {column}")


def _empty_text_mask(values: pd.Series) -> pd.Series:
    stripped = values.fillna(EMPTY_CELL).astype(str).str.strip()
    return (stripped == EMPTY_CELL) | (stripped.str.lower() == NAN_CELL)


def _id_values(catalog: pd.DataFrame) -> list[str]:
    return catalog[POST_ID_COLUMN].astype(str).tolist()


def _require_columns(frame: pd.DataFrame, column_names: tuple[str, ...]) -> None:
    missing = [name for name in column_names if name not in frame.columns]
    if missing:
        raise ValueError(f"missing column {missing[0]}")
