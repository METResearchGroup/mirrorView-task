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

KNOWN_INTEGRATIONS = frozenset(
    {INTEGRATION_BLUESKY, INTEGRATION_REDDIT, INTEGRATION_TWITTER}
)

_INTEGRATION_PRIMARY_KEY_COLUMNS: dict[str, str] = {
    INTEGRATION_BLUESKY: BLUESKY_COLUMNS.records_id_column,
    INTEGRATION_TWITTER: TWITTER_COLUMNS.records_id_column,
}


def generate_record_id(integration: str, primary_key: str) -> str:
    """Return the stable ``{integration}_{id}`` key used across study datasets.

    Bluesky hashes ``uri`` with SHA-256. Twitter and Reddit prefix the given
    primary key string unchanged.

    Parameters
    ----------
    integration
        Platform name: ``bluesky``, ``reddit``, or ``twitter``.
    primary_key
        Platform-native unique id for the row. Reddit comments use
        ``comment_fullname``.

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
    if normalized_integration not in KNOWN_INTEGRATIONS:
        raise ValueError(f"Unknown integration `{integration}`.")

    normalized_primary_key = str(primary_key).strip()
    if not normalized_primary_key:
        raise ValueError("Primary key must be a non-empty string.")

    if normalized_integration == INTEGRATION_BLUESKY:
        digest = hashlib.sha256(normalized_primary_key.encode("utf-8")).hexdigest()
        return f"{INTEGRATION_BLUESKY}_{digest}"

    return f"{normalized_integration}_{normalized_primary_key}"


def generate_reddit_record_id(row: Mapping[str, Any]) -> str:
    """Return ``record_id`` for a Reddit comment row.

    The id is ``reddit_`` followed by the row's ``comment_fullname``.

    Parameters
    ----------
    row
        A Reddit ingest row. The row must include ``comment_fullname``.

    Returns
    -------
    str
        Stable Reddit record id.

    Raises
    ------
    KeyError
        When ``comment_fullname`` is missing from the row.
    ValueError
        When ``comment_fullname`` is empty.
    """
    comment_fullname_column = REDDIT_COLUMNS.records_id_column
    if comment_fullname_column not in row:
        raise KeyError(comment_fullname_column)

    comment_fullname = str(row[comment_fullname_column]).strip()
    if not comment_fullname:
        raise ValueError("Reddit comments need comment_fullname.")
    return generate_record_id(INTEGRATION_REDDIT, comment_fullname)


def attach_record_id(row: Mapping[str, Any], integration: str) -> dict[str, Any]:
    """Return a copy of ``row`` with ``record_id`` set from the platform primary key.

    Reddit rows go through :func:`generate_reddit_record_id`. Bluesky and Twitter
    rows use the usual platform id column.

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
    if normalized_integration not in KNOWN_INTEGRATIONS:
        raise ValueError(f"Unknown integration `{integration}`.")

    if normalized_integration == INTEGRATION_REDDIT:
        record_id = generate_reddit_record_id(row)
    else:
        primary_key_column = _INTEGRATION_PRIMARY_KEY_COLUMNS[normalized_integration]
        if primary_key_column not in row:
            raise KeyError(primary_key_column)
        record_id = generate_record_id(
            normalized_integration,
            str(row[primary_key_column]),
        )

    out = dict(row)
    out[RECORD_ID_COLUMN] = record_id
    return out
