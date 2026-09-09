"""Sample catalog cells and map columns to the old catalog schema."""

from __future__ import annotations

import pandas as pd

from experiments.curate_study_2_phase_3_stimuli.sources import (
    CATALOG_COLUMNS,
    CELL_TARGET,
    EMPTY_CELL,
    MIRRORED_TEXT_COLUMN,
    ORIGINAL_TEXT_COLUMN,
    POST_PRIMARY_KEY_COLUMN,
    RECORD_ID_COLUMN,
    SAMPLE_SEED,
    SAMPLE_TOXICITY_TYPE_COLUMN,
    SAMPLED_STANCE_COLUMN,
    SORT_KIND,
    STANCE_COLUMN,
    STANCE_VALUES,
    TEXT_COLUMN,
    TOXICITY_COLUMN,
    TOXICITY_LABELS,
    TOXICITY_TIERS,
)


def sample_catalog(pool: pd.DataFrame) -> pd.DataFrame:
    """Sample each stance by toxicity cell and map rows to catalog columns.

    Parameters
    ----------
    pool
        Posts that already have a successful flip.

    Returns
    -------
    pd.DataFrame
        Catalog rows in old-catalog column order, sorted by
        ``post_primary_key``.

    Raises
    ------
    ValueError
        When a cell is short, original text disagrees with post text, or
        ``mirrored_text`` is empty.
    """
    parts = [_sample_one_cell(pool, stance, tier) for stance, tier in _cells()]
    catalog = pd.concat(parts, ignore_index=True)
    mapped = _map_catalog_columns(catalog)
    return mapped.sort_values(POST_PRIMARY_KEY_COLUMN, kind=SORT_KIND).reset_index(
        drop=True
    )


def _cells() -> tuple[tuple[str, str], ...]:
    return tuple((stance, tier) for stance in STANCE_VALUES for tier in TOXICITY_TIERS)


def _sample_one_cell(pool: pd.DataFrame, stance: str, tier: str) -> pd.DataFrame:
    cell = pool.loc[_cell_mask(pool, stance, tier)]
    needed = CELL_TARGET[stance][tier]
    if len(cell) < needed:
        raise ValueError(f"short cell stance={stance} tier={tier} have={len(cell)}")
    return cell.sample(n=needed, random_state=SAMPLE_SEED, replace=False)


def _cell_mask(pool: pd.DataFrame, stance: str, tier: str) -> pd.Series:
    return (pool[STANCE_COLUMN] == stance) & (pool[TOXICITY_COLUMN] == tier)


def _map_catalog_columns(sampled: pd.DataFrame) -> pd.DataFrame:
    mapped = pd.DataFrame(
        {
            POST_PRIMARY_KEY_COLUMN: sampled[RECORD_ID_COLUMN].astype(str),
            ORIGINAL_TEXT_COLUMN: sampled[ORIGINAL_TEXT_COLUMN].astype(str),
            SAMPLE_TOXICITY_TYPE_COLUMN: sampled[TOXICITY_COLUMN].map(TOXICITY_LABELS),
            SAMPLED_STANCE_COLUMN: sampled[STANCE_COLUMN].astype(str),
            MIRRORED_TEXT_COLUMN: sampled[MIRRORED_TEXT_COLUMN].astype(str),
        }
    )
    _require_mapped_text(sampled, mapped)
    return mapped.loc[:, list(CATALOG_COLUMNS)]


def _require_mapped_text(sampled: pd.DataFrame, mapped: pd.DataFrame) -> None:
    post_text = sampled[TEXT_COLUMN].astype(str).to_numpy()
    original = mapped[ORIGINAL_TEXT_COLUMN].to_numpy()
    if not (post_text == original).all():
        raise ValueError("original_text does not match post text")
    if mapped[SAMPLE_TOXICITY_TYPE_COLUMN].isna().any():
        raise ValueError("unmapped llm_toxicity_tier")
    mirrored = mapped[MIRRORED_TEXT_COLUMN].astype(str).str.strip()
    if (mirrored == EMPTY_CELL).any():
        raise ValueError("empty mirrored_text")
