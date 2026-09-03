"""Build stable ``{integration}_{id}`` record ids for ingest writes.

Run this import from the repo root with

    PYTHONPATH=. uv run python -c \\
        "from data_platform.ingestion.generate_record_id import generate_record_id"
"""

from __future__ import annotations

import hashlib
from typing import Any, Mapping

from data_platform.utils.platform_specific_columns import (
    BLUESKY_COLUMNS,
    REDDIT_COLUMNS,
    TWITTER_COLUMNS,
)

RECORD_ID_COLUMN = "record_id"

INTEGRATION_BLUESKY = "bluesky"
INTEGRATION_REDDIT = "reddit"
INTEGRATION_TWITTER = "twitter"

_INTEGRATION_PRIMARY_KEY_COLUMNS: dict[str, str] = {
    INTEGRATION_BLUESKY: BLUESKY_COLUMNS.records_id_column,
    INTEGRATION_REDDIT: REDDIT_COLUMNS.records_id_column,
    INTEGRATION_TWITTER: TWITTER_COLUMNS.records_id_column,
}


def generate_record_id(integration: str, primary_key: str) -> str:
    """Return the stable ``{integration}_{id}`` key used across study datasets.

    Bluesky hashes ``uri`` with SHA-256. Twitter and Reddit use the platform
    primary key string unchanged.

    Parameters
    ----------
    integration
        Platform name: ``bluesky``, ``reddit``, or ``twitter``.
    primary_key
        Platform-native unique id for the row (for example Bluesky ``uri``,
        Reddit ``comment_fullname``, or Twitter ``tweet_id``).

    Returns
    -------
    str
        Stable record id with the integration prefix.

    Raises
    ------
    ValueError
        When ``integration`` is unknown or ``primary_key`` is empty.
    """
    normalized_integration = integration.strip().lower()
    if normalized_integration not in _INTEGRATION_PRIMARY_KEY_COLUMNS:
        raise ValueError(f"Unknown integration `{integration}`.")

    normalized_primary_key = str(primary_key).strip()
    if not normalized_primary_key:
        raise ValueError("Primary key must be a non-empty string.")

    if normalized_integration == INTEGRATION_BLUESKY:
        digest = hashlib.sha256(normalized_primary_key.encode("utf-8")).hexdigest()
        return f"{INTEGRATION_BLUESKY}_{digest}"

    return f"{normalized_integration}_{normalized_primary_key}"


def attach_record_id(row: Mapping[str, Any], integration: str) -> dict[str, Any]:
    """Return a copy of ``row`` with ``record_id`` set from the platform primary key.

    Parameters
    ----------
    row
        One ingest record dict. Must include the platform primary key column.
    integration
        Platform name passed to :func:`generate_record_id`.

    Returns
    -------
    dict[str, Any]
        A new dict equal to ``row`` plus ``record_id``.

    Raises
    ------
    KeyError
        When the platform primary key column is missing from ``row``.
    ValueError
        When ``integration`` is unknown or the primary key value is empty.
    """
    normalized_integration = integration.strip().lower()
    primary_key_column = _INTEGRATION_PRIMARY_KEY_COLUMNS.get(normalized_integration)
    if primary_key_column is None:
        raise ValueError(f"Unknown integration `{integration}`.")

    if primary_key_column not in row:
        raise KeyError(primary_key_column)

    out = dict(row)
    out[RECORD_ID_COLUMN] = generate_record_id(
        normalized_integration,
        str(row[primary_key_column]),
    )
    return out
