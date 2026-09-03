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
REDDIT_POST_RECORDS_ID_COLUMN = "reddit_fullname"
REDDIT_COMMENT_POST_ID_COLUMN = "post_reddit_id"
REDDIT_COMMENT_ID_COLUMN = "comment_id"
REDDIT_COMMENTS_FILE_STEM = "comments"

INTEGRATION_BLUESKY = "bluesky"
INTEGRATION_REDDIT = "reddit"
INTEGRATION_TWITTER = "twitter"

_INTEGRATION_PRIMARY_KEY_COLUMNS: dict[str, str] = {
    INTEGRATION_BLUESKY: BLUESKY_COLUMNS.records_id_column,
    INTEGRATION_REDDIT: REDDIT_COLUMNS.records_id_column,
    INTEGRATION_TWITTER: TWITTER_COLUMNS.records_id_column,
}


def resolve_records_id_column(platform: str, records_file_stem: str) -> str:
    """Return the platform primary-key column for one ingest records file.

    Parameters
    ----------
    platform
        Platform name: ``bluesky``, ``reddit``, or ``twitter``.
    records_file_stem
        Records filename stem, for example ``posts`` or ``comments``.

    Returns
    -------
    str
        Column name whose value feeds :func:`generate_record_id`.

    Raises
    ------
    ValueError
        When ``platform`` is unknown.
    """
    normalized_platform = platform.strip().lower()
    if normalized_platform == INTEGRATION_BLUESKY:
        return BLUESKY_COLUMNS.records_id_column
    if normalized_platform == INTEGRATION_TWITTER:
        return TWITTER_COLUMNS.records_id_column
    if normalized_platform == INTEGRATION_REDDIT:
        if records_file_stem == "posts":
            return REDDIT_POST_RECORDS_ID_COLUMN
        return REDDIT_COLUMNS.records_id_column
    raise ValueError(f"Unknown platform `{platform}`.")


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
        Reddit ``{post_reddit_id}_{comment_id}`` for comments or
        ``reddit_fullname`` for posts, or Twitter ``tweet_id``).

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


def resolve_primary_key_value(
    row: Mapping[str, Any],
    integration: str,
    *,
    records_file_stem: str | None = None,
    primary_key_column: str | None = None,
) -> str:
    """Return the string that feeds :func:`generate_record_id` for one ingest row.

    Parameters
    ----------
    row
        One ingest record dict.
    integration
        Platform name: ``bluesky``, ``reddit``, or ``twitter``.
    records_file_stem
        Records filename stem, for example ``posts`` or ``comments``.
    primary_key_column
        Optional override for the source column on non-composite rows.

    Returns
    -------
    str
        Primary key value before the integration prefix is applied.

    Raises
    ------
    KeyError
        When a required source column is missing from ``row``.
    ValueError
        When ``integration`` is unknown or a required value is empty.
    """
    normalized_integration = integration.strip().lower()
    if (
        normalized_integration == INTEGRATION_REDDIT
        and records_file_stem == REDDIT_COMMENTS_FILE_STEM
    ):
        post_id = str(row[REDDIT_COMMENT_POST_ID_COLUMN]).strip()
        comment_id = str(row[REDDIT_COMMENT_ID_COLUMN]).strip()
        if not post_id or not comment_id:
            raise ValueError("Reddit comments need post_reddit_id and comment_id.")
        return f"{post_id}_{comment_id}"

    resolved_stem = records_file_stem or REDDIT_COMMENTS_FILE_STEM
    resolved_column = primary_key_column or resolve_records_id_column(
        integration,
        resolved_stem,
    )
    if resolved_column not in row:
        raise KeyError(resolved_column)

    primary_key = str(row[resolved_column]).strip()
    if not primary_key:
        raise ValueError("Primary key must be a non-empty string.")
    return primary_key


def attach_record_id(
    row: Mapping[str, Any],
    integration: str,
    *,
    records_file_stem: str | None = None,
    primary_key_column: str | None = None,
) -> dict[str, Any]:
    """Return a copy of ``row`` with ``record_id`` set from the platform primary key.

    Parameters
    ----------
    row
        One ingest record dict. Must include the platform primary key column.
    integration
        Platform name passed to :func:`generate_record_id`.
    records_file_stem
        Records filename stem when one integration writes multiple record types.
    primary_key_column
        Optional override for the source column on non-composite rows.

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
    if normalized_integration not in _INTEGRATION_PRIMARY_KEY_COLUMNS:
        raise ValueError(f"Unknown integration `{integration}`.")

    primary_key_value = resolve_primary_key_value(
        row,
        integration,
        records_file_stem=records_file_stem,
        primary_key_column=primary_key_column,
    )

    out = dict(row)
    out[RECORD_ID_COLUMN] = generate_record_id(
        normalized_integration,
        primary_key_value,
    )
    return out
