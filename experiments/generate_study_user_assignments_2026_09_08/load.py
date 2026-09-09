"""Load remaining labels and join them to catalog cell membership.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
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
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    NewCatalogSource,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.load import (
    load_new_catalog,
)
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    CACHE_FILENAME,
    CATALOG_COLUMNS,
    CATALOG_SHUFFLE_SEED,
    CELL_BY_STANCE_TOXICITY,
    CELL_COLUMN,
    CSV_INDEX,
    OLD_STIMULI_DATASET,
    PINNED_REMAINING_LABEL_COUNT,
    PINNED_REMAINING_LABELS_S3_URI,
    PINNED_REMAINING_LABELS_SHA256,
    PINNED_REMAINING_POST_COUNT,
    POST_ID_COLUMN,
    REMAINING_COLUMNS,
    REMAINING_COUNT_COLUMN,
    REMAINING_ID_COLUMN,
    S3_URI_PREFIX,
    SHUFFLED_COLUMNS,
    SHUFFLED_FILENAME,
    STANCE_COLUMN,
    TOXICITY_COLUMN,
)
from shared.data.dataloader import load_dataset


def load_remaining_labels(
    path: str, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    """Load remaining labels from a local CSV or an S3 URI.

    Parameters
    ----------
    path
        Local path or S3 URI. The pinned remaining-labels URI is hash-checked.
    store
        Object store used only for S3 remaining-label files.
    cache_dir
        Directory for a local copy of downloaded bytes.

    Returns
    -------
    pd.DataFrame
        Remaining-label rows with unique ids and remaining counts greater than 0.

    Raises
    ------
    FileNotFoundError
        When the source object or local file is missing.
    ValueError
        When columns, uniqueness, remaining counts, or the pinned hash do not match.
    """
    frame = _read_remaining_frame(path, store, cache_dir)
    _validate_remaining(frame)
    if path == PINNED_REMAINING_LABELS_S3_URI:
        _require_pinned_totals(frame)
    return frame


def load_old_catalog_with_cells() -> pd.DataFrame:
    """Load old catalog rows with stance and toxicity columns.

    Returns
    -------
    pd.DataFrame
        Catalog rows with ``post_primary_key``, ``sampled_stance``, and
        ``sample_toxicity_type``.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    catalog = load_dataset(OLD_STIMULI_DATASET)
    _require_columns(catalog, CATALOG_COLUMNS)
    return catalog.loc[:, list(CATALOG_COLUMNS)]


def load_new_catalog_with_cells(
    source: NewCatalogSource, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    """Download the pinned new catalog and keep cell columns.

    Parameters
    ----------
    source
        Pinned catalog URI, SHA-256, and row count.
    store
        Object store used only to download the pinned catalog.
    cache_dir
        Directory for a local copy of the catalog bytes.

    Returns
    -------
    pd.DataFrame
        Catalog rows with ``post_primary_key``, ``sampled_stance``, and
        ``sample_toxicity_type``.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, or required columns do not match.
    """
    catalog = load_new_catalog(source, store, cache_dir)
    _require_columns(catalog, CATALOG_COLUMNS)
    return catalog.loc[:, list(CATALOG_COLUMNS)]


def join_remaining_to_catalogs(
    remaining: pd.DataFrame, old_catalog: pd.DataFrame, new_catalog: pd.DataFrame
) -> pd.DataFrame:
    """Join remaining label ids to exactly one catalog cell.

    Parameters
    ----------
    remaining
        Remaining-label table.
    old_catalog
        Old catalog with cell columns.
    new_catalog
        New catalog with cell columns.

    Returns
    -------
    pd.DataFrame
        One row per remaining id with cell membership.

    Raises
    ------
    ValueError
        When an id is in neither catalog or in both catalogs.
    """
    old_by_id = _catalog_rows_by_id(old_catalog)
    new_by_id = _catalog_rows_by_id(new_catalog)
    rows = [
        _joined_row(remaining_id, remaining_count, old_by_id, new_by_id)
        for remaining_id, remaining_count in zip(
            remaining[REMAINING_ID_COLUMN].astype(str),
            remaining[REMAINING_COUNT_COLUMN].astype(int),
        )
    ]
    return pd.DataFrame(rows)


def _catalog_rows_by_id(catalog: pd.DataFrame) -> dict[str, pd.Series]:
    return {
        str(row[POST_ID_COLUMN]): row
        for _, row in catalog.iterrows()
    }


def _joined_row(
    remaining_id: str,
    remaining_count: int,
    old_by_id: dict[str, pd.Series],
    new_by_id: dict[str, pd.Series],
) -> dict[str, object]:
    catalog_row = _exclusive_catalog_row(remaining_id, old_by_id, new_by_id)
    stance = str(catalog_row[STANCE_COLUMN])
    toxicity = str(catalog_row[TOXICITY_COLUMN])
    return {
        POST_ID_COLUMN: remaining_id,
        STANCE_COLUMN: stance,
        TOXICITY_COLUMN: toxicity,
        REMAINING_COUNT_COLUMN: remaining_count,
        CELL_COLUMN: CELL_BY_STANCE_TOXICITY[(stance, toxicity)],
    }


def _exclusive_catalog_row(
    remaining_id: str,
    old_by_id: dict[str, pd.Series],
    new_by_id: dict[str, pd.Series],
) -> pd.Series:
    in_old = remaining_id in old_by_id
    in_new = remaining_id in new_by_id
    if in_old == in_new:
        raise ValueError(f"remaining id {remaining_id} must be in exactly one catalog")
    if in_old:
        return old_by_id[remaining_id]
    return new_by_id[remaining_id]


def _read_remaining_frame(
    path: str, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    if path.startswith(S3_URI_PREFIX):
        return pd.read_csv(io.BytesIO(_remaining_bytes(path, store, cache_dir)))
    return pd.read_csv(path)


def _remaining_bytes(path: str, store: CampaignObjectStore, cache_dir: Path) -> bytes:
    cache_path = cache_dir / CACHE_FILENAME
    if cache_path.is_file() and path == PINNED_REMAINING_LABELS_S3_URI:
        cached = cache_path.read_bytes()
        if sha256_hex(cached) == PINNED_REMAINING_LABELS_SHA256:
            return cached
    body = _download_remaining_bytes(path, store)
    if path == PINNED_REMAINING_LABELS_S3_URI:
        _require_remaining_hash(path, body)
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path.write_bytes(body)
    return body


def _download_remaining_bytes(path: str, store: CampaignObjectStore) -> bytes:
    _bucket, key = parse_s3_uri(path)
    stored = store.get(key)
    if stored is None:
        raise FileNotFoundError(path)
    return stored.body


def _require_remaining_hash(path: str, body: bytes) -> None:
    if sha256_hex(body) != PINNED_REMAINING_LABELS_SHA256:
        raise ValueError(f"SHA-256 mismatch for {path}")


def _validate_remaining(frame: pd.DataFrame) -> None:
    _require_columns(frame, REMAINING_COLUMNS)
    ids = frame[REMAINING_ID_COLUMN].astype(str)
    if int(ids.nunique()) != len(ids):
        raise ValueError("duplicate remaining id")
    if int((frame[REMAINING_COUNT_COLUMN].astype(int) < 1).sum()) > 0:
        raise ValueError("remaining count is less than 1")


def _require_pinned_totals(frame: pd.DataFrame) -> None:
    label_count = int(frame[REMAINING_COUNT_COLUMN].sum())
    if len(frame) != PINNED_REMAINING_POST_COUNT:
        raise ValueError("pinned remaining post count mismatch")
    if label_count != PINNED_REMAINING_LABEL_COUNT:
        raise ValueError("pinned remaining label count mismatch")


def _require_columns(frame: pd.DataFrame, column_names: tuple[str, ...]) -> None:
    missing = [name for name in column_names if name not in frame.columns]
    if missing:
        raise ValueError(f"missing column {missing[0]}")


def write_shuffled_stimuli(joined: pd.DataFrame, experiment_dir: Path) -> Path:
    """Write the seed-0 shuffled joined table locally.

    Parameters
    ----------
    joined
        Joined remaining-label rows already shuffled.
    experiment_dir
        Folder that receives ``shuffled_stimuli.csv``.

    Returns
    -------
    Path
        Path of the written file.
    """
    shuffled = joined.sample(frac=1, random_state=CATALOG_SHUFFLE_SEED).reset_index(
        drop=True
    )
    path = experiment_dir / SHUFFLED_FILENAME
    shuffled.loc[:, list(SHUFFLED_COLUMNS)].to_csv(path, index=CSV_INDEX)
    return path
