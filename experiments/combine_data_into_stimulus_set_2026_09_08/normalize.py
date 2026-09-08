"""Map one curated export onto the shared stimulus columns."""

from __future__ import annotations

import pandas as pd

from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_COLUMNS,
    CuratedSource,
)

PASSTHROUGH_COLUMNS = (
    "record_id",
    "source_record_id",
    "author_handle",
    "text",
    "created_at",
    "sync_timestamp",
    "news_or_opinion_category",
    "is_political",
    "is_likely_spam",
    "is_self_contained",
    "is_structurally_complete",
    "political_stance",
    "llm_toxicity_tier",
)
INTEGRATION_COLUMN = "integration"
SOURCE_DATASET_ID_COLUMN = "source_dataset_id"
SOURCE_CURATED_RUN_COLUMN = "source_curated_run"
PLATFORM_ID_COLUMN = "platform_id"


def normalize_curated_frame(frame: pd.DataFrame, source: CuratedSource) -> pd.DataFrame:
    """Return one source table with the shared 17-column schema.

    Parameters
    ----------
    frame
        Curated export as downloaded.
    source
        Pinned identity used to fill platform and source columns.

    Returns
    -------
    pd.DataFrame
        Table with the shared combine columns in contract order.

    Raises
    ------
    ValueError
        When a required column is missing.
    """
    _require_source_columns(frame, source)
    identity = _source_identity_frame(frame, source)
    passthrough = frame.loc[:, list(PASSTHROUGH_COLUMNS)]
    normalized = pd.concat([identity, passthrough], axis=1)
    return normalized.loc[:, list(COMBINED_COLUMNS)]


def _require_source_columns(frame: pd.DataFrame, source: CuratedSource) -> None:
    required = (*PASSTHROUGH_COLUMNS, source.platform_id_column)
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise ValueError(f"missing columns {missing} uri={source.s3_uri}")


def _source_identity_frame(frame: pd.DataFrame, source: CuratedSource) -> pd.DataFrame:
    return pd.DataFrame(
        {
            INTEGRATION_COLUMN: source.integration.value,
            SOURCE_DATASET_ID_COLUMN: source.dataset_id,
            SOURCE_CURATED_RUN_COLUMN: source.curated_run,
            PLATFORM_ID_COLUMN: frame[source.platform_id_column].to_numpy(),
        },
        index=frame.index,
    )
