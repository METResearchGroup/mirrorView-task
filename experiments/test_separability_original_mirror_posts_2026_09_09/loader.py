"""Download the pinned catalog and build the shuffled presentation table.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import io
import random
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    CACHE_FILENAME,
    CATALOG_REQUIRED_COLUMNS,
    CatalogSource,
    EMPTY_CELL,
    FIRST_TEXT_COLUMN,
    GOLD_HUMAN_SLOT_COLUMN,
    GoldHumanSlot,
    ID_COLUMN,
    MIRRORED_TEXT_COLUMN,
    NAN_CELL,
    ORIGINAL_TEXT_COLUMN,
    PRESENTATION_COLUMNS,
    PRESENTATION_S3_KEY,
    PROMPT_TEXT_COLUMN,
    SAMPLED_STANCE_COLUMN,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    SECOND_TEXT_COLUMN,
    SHUFFLE_SEED,
    SMOKE_ROW_COUNT,
    SORT_KIND,
    VALID_SAMPLED_STANCES,
    VALID_SAMPLE_TOXICITY_TYPES,
)
from experiments.test_separability_original_mirror_posts_2026_09_09.prompts import (
    format_user_prompt,
)


def load_catalog(
    source: CatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> pd.DataFrame:
    """Download the pinned catalog CSV and validate its identity.

    Parameters
    ----------
    source
        Pinned CSV URI, SHA-256, and row count.
    store
        Object store used only to download the pinned CSV.
    cache_dir
        Directory for a local copy of the source bytes.

    Returns
    -------
    pd.DataFrame
        Catalog rows with validated ids and required columns.

    Raises
    ------
    FileNotFoundError
        When the source object is missing.
    ValueError
        When the SHA-256, row count, id uniqueness, or column values do not match.
    """
    body = _bytes_matching_pinned_hash(source, store, cache_dir)
    frame = pd.read_csv(io.BytesIO(body))
    _validate_catalog_frame(frame, source)
    return frame


def build_presentation_table(catalog: pd.DataFrame) -> pd.DataFrame:
    """Shuffle each original and mirror pair once and build presentation rows.

    Parameters
    ----------
    catalog
        Validated catalog rows.

    Returns
    -------
    pd.DataFrame
        Presentation rows with gold order and prompt text.
    """
    rng = random.Random(SHUFFLE_SEED)
    ordered = catalog.sort_values(ID_COLUMN, kind=SORT_KIND)
    rows = [_presentation_row(rng, row) for _, row in ordered.iterrows()]
    return pd.DataFrame(rows, columns=list(PRESENTATION_COLUMNS))


def _presentation_row(rng: random.Random, row: pd.Series) -> dict[str, str]:
    original = str(row[ORIGINAL_TEXT_COLUMN]).strip()
    mirror = str(row[MIRRORED_TEXT_COLUMN]).strip()
    if rng.getrandbits(1) == 0:
        first_text = original
        second_text = mirror
        gold_slot = GoldHumanSlot.FIRST.value
    else:
        first_text = mirror
        second_text = original
        gold_slot = GoldHumanSlot.SECOND.value
    return {
        ID_COLUMN: str(row[ID_COLUMN]).strip(),
        FIRST_TEXT_COLUMN: first_text,
        SECOND_TEXT_COLUMN: second_text,
        GOLD_HUMAN_SLOT_COLUMN: gold_slot,
        SAMPLED_STANCE_COLUMN: str(row[SAMPLED_STANCE_COLUMN]).strip(),
        SAMPLE_TOXICITY_TYPE_COLUMN: str(row[SAMPLE_TOXICITY_TYPE_COLUMN]).strip(),
        PROMPT_TEXT_COLUMN: format_user_prompt(first_text, second_text),
    }


def load_presentations(store: CampaignObjectStore) -> pd.DataFrame:
    """Load the shared presentation parquet from S3.

    Parameters
    ----------
    store
        Object store that holds ``presentations.parquet``.

    Returns
    -------
    pd.DataFrame
        Presentation rows with the required columns.

    Raises
    ------
    FileNotFoundError
        When the presentation object is missing.
    """
    stored = store.get(PRESENTATION_S3_KEY)
    if stored is None:
        raise FileNotFoundError(PRESENTATION_S3_KEY)
    return pd.read_parquet(io.BytesIO(stored.body))


def smoke_presentations(presentations: pd.DataFrame) -> pd.DataFrame:
    """Return the first smoke rows after sorting by post_primary_key.

    Parameters
    ----------
    presentations
        Full presentation table.

    Returns
    -------
    pd.DataFrame
        First ``SMOKE_ROW_COUNT`` rows in id order.
    """
    ordered = presentations.sort_values(ID_COLUMN, kind=SORT_KIND)
    return ordered.head(SMOKE_ROW_COUNT).reset_index(drop=True)


def _validate_catalog_frame(frame: pd.DataFrame, source: CatalogSource) -> None:
    for column in CATALOG_REQUIRED_COLUMNS:
        _require_column(frame, column)
    if len(frame) != source.expected_row_count:
        raise ValueError(
            f"row_count={len(frame)} expected={source.expected_row_count}"
        )
    ids = _stripped_nonempty(frame[ID_COLUMN])
    _require_unique_id_count(ids, source.expected_row_count, ID_COLUMN)
    _validate_catalog_values(frame)


def _validate_catalog_values(frame: pd.DataFrame) -> None:
    for _, row in frame.iterrows():
        _require_nonempty_text(row[ORIGINAL_TEXT_COLUMN], ORIGINAL_TEXT_COLUMN)
        _require_nonempty_text(row[MIRRORED_TEXT_COLUMN], MIRRORED_TEXT_COLUMN)
        stance = str(row[SAMPLED_STANCE_COLUMN]).strip()
        if stance not in VALID_SAMPLED_STANCES:
            raise ValueError(f"invalid {SAMPLED_STANCE_COLUMN}={stance}")
        toxicity = str(row[SAMPLE_TOXICITY_TYPE_COLUMN]).strip()
        if toxicity not in VALID_SAMPLE_TOXICITY_TYPES:
            raise ValueError(f"invalid {SAMPLE_TOXICITY_TYPE_COLUMN}={toxicity}")


def _require_nonempty_text(value: object, column_name: str) -> None:
    text = str(value).strip() if value is not None else EMPTY_CELL
    if text == EMPTY_CELL or text.lower() == NAN_CELL:
        raise ValueError(f"empty {column_name}")


def _object_key(source: CatalogSource) -> str:
    _bucket, key = parse_s3_uri(source.s3_uri)
    return key


def _cache_path(cache_dir: Path) -> Path:
    return cache_dir / CACHE_FILENAME


def _download_source_bytes(source: CatalogSource, store: CampaignObjectStore) -> bytes:
    stored = store.get(_object_key(source))
    if stored is None:
        raise FileNotFoundError(source.s3_uri)
    return stored.body


def _bytes_matching_pinned_hash(
    source: CatalogSource,
    store: CampaignObjectStore,
    cache_dir: Path,
) -> bytes:
    cache_path = _cache_path(cache_dir)
    if cache_path.is_file():
        cached = cache_path.read_bytes()
        if sha256_hex(cached) == source.sha256:
            return cached
    body = _download_source_bytes(source, store)
    if sha256_hex(body) != source.sha256:
        raise ValueError(f"SHA-256 mismatch for {source.s3_uri}")
    cache_dir.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    return body


def _require_column(frame: pd.DataFrame, column_name: str) -> None:
    if column_name not in frame.columns:
        raise ValueError(f"missing column {column_name}")


def _stripped_nonempty(values: pd.Series) -> pd.Series:
    stripped = values.fillna(EMPTY_CELL).astype(str).str.strip()
    nonempty = (stripped != EMPTY_CELL) & (stripped.str.lower() != NAN_CELL)
    return stripped.loc[nonempty]


def _require_unique_id_count(
    ids: pd.Series, expected_count: int, column_name: str
) -> None:
    unique_count = int(ids.nunique())
    if unique_count != len(ids):
        raise ValueError(f"duplicate {column_name}")
    if unique_count != expected_count:
        raise ValueError(f"{column_name} count={unique_count} expected={expected_count}")
