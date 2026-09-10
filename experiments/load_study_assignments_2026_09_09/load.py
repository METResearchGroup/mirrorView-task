"""Download the pinned assignment CSV with a SHA-256 check.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNED_POST_IDS_COLUMN,
    ASSIGNMENT_COLUMNS,
    ASSIGNMENT_ID_COLUMN,
    AssignmentRow,
    CACHE_FILENAME,
    CONDITION_COLUMN,
    CREATED_AT_COLUMN,
    EMPTY_POLITICAL_PARTY,
    EXPECTED_SOURCE_ROWS,
    NAN_CELL,
    PINNED_ASSIGNMENTS_S3_URI,
    PINNED_ASSIGNMENTS_SHA256,
    POLITICAL_PARTY_COLUMN,
)
from experiments.load_study_assignments_2026_09_09.split import (
    require_training_assisted,
)


def load_source_assignments(
    store: CampaignObjectStore, cache_dir: Path
) -> list[AssignmentRow]:
    """Download the pinned assignment CSV and return one row per user.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, columns, or row count does not match.
    """
    frame = pd.read_csv(io.BytesIO(_bytes_matching_hash(store, cache_dir)))
    rows = _rows_from_frame(frame)
    _require_source_row_count(rows)
    require_training_assisted(rows)
    return rows


def _bytes_matching_hash(store: CampaignObjectStore, cache_dir: Path) -> bytes:
    cache_path = cache_dir / CACHE_FILENAME
    if cache_path.is_file():
        cached = cache_path.read_bytes()
        if sha256_hex(cached) == PINNED_ASSIGNMENTS_SHA256:
            return cached
    body = _download_source_bytes(store)
    if sha256_hex(body) != PINNED_ASSIGNMENTS_SHA256:
        raise ValueError(f"SHA-256 mismatch for {PINNED_ASSIGNMENTS_S3_URI}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    return body


def _download_source_bytes(store: CampaignObjectStore) -> bytes:
    _, key = parse_s3_uri(PINNED_ASSIGNMENTS_S3_URI)
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(PINNED_ASSIGNMENTS_S3_URI)
    return stored.body


def _rows_from_frame(frame: pd.DataFrame) -> list[AssignmentRow]:
    _require_columns(frame, ASSIGNMENT_COLUMNS)
    return [_assignment_from_mapping(record) for record in frame.to_dict("records")]


def _assignment_from_mapping(record: dict[str, object]) -> AssignmentRow:
    return AssignmentRow(
        id=str(record[ASSIGNMENT_ID_COLUMN]),
        assigned_post_ids=str(record[ASSIGNED_POST_IDS_COLUMN]),
        political_party=_party_cell(record[POLITICAL_PARTY_COLUMN]),
        condition=str(record[CONDITION_COLUMN]),
        created_at=str(record[CREATED_AT_COLUMN]),
    )


def _party_cell(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return EMPTY_POLITICAL_PARTY
    text = str(value).strip()
    if text.lower() == NAN_CELL:
        return EMPTY_POLITICAL_PARTY
    return text


def _require_source_row_count(rows: list[AssignmentRow]) -> None:
    if len(rows) != EXPECTED_SOURCE_ROWS:
        raise ValueError(f"source rows={len(rows)} expected={EXPECTED_SOURCE_ROWS}")


def _require_columns(frame: pd.DataFrame, column_names: tuple[str, ...]) -> None:
    missing = [name for name in column_names if name not in frame.columns]
    if missing:
        raise ValueError(f"missing column {missing[0]}")
