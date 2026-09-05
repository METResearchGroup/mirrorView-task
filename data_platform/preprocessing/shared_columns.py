"""Shared column helpers used across platform preprocessing pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_AUTHOR_HANDLE_COLUMN,
    STANDARDIZED_SOURCE_RECORD_ID_COLUMN,
)

if TYPE_CHECKING:
    from data_platform.preprocessing.runner import PreprocessPlatformSpec


def add_standardized_author_columns(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Copy the platform author-handle source column onto shared ``author_handle``.

    Each platform stores the handle in a different column in raw storage. Reddit
    stores ``author``, Twitter stores ``author_id``, and Bluesky stores
    ``author_handle``. Downstream preprocessing, feature extraction, and curation
    pipelines read a single column named ``author_handle``. This helper copies the
    value from the platform-specific source column named on the specification, and
    it overwrites any existing ``author_handle`` value.

    Original platform columns, for example Reddit ``author`` or Twitter
    ``username`` and ``author_id``, are left unchanged. ``author_id`` is not added or modified.

    Parameters
    ----------
    spec
        ``author_handle_source_column`` names the column to copy from. The
        destination is always shared ``author_handle``.

    Returns
    -------
    pd.DataFrame
        A new frame that includes ``author_handle``.

    Raises
    ------
    KeyError
        When ``author_handle_source_column`` is missing from the frame.
    """
    out = df.copy()
    source_column = spec.author_handle_source_column
    original_handle = out[source_column]
    out[STANDARDIZED_AUTHOR_HANDLE_COLUMN] = original_handle.map(lambda value: str(value))
    return out


def add_standardized_source_record_id(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Copy the platform's original record id onto the shared ``source_record_id`` column.

    You still have original fields such as Bluesky ``uri``, Reddit
    ``comment_fullname``, and Twitter ``tweet_id`` on the returned frame. The
    function does not modify the input frame.

    Parameters
    ----------
    spec
        ``spec.columns.records_id_column`` is the copy source. The destination
        is always shared ``source_record_id``.

    Returns
    -------
    pd.DataFrame
        A new frame that includes ``source_record_id``.

    Raises
    ------
    KeyError
        When the original record id column is missing from the frame.
    """
    out = df.copy()
    source_column = spec.columns.records_id_column
    original_id = out[source_column]
    out[STANDARDIZED_SOURCE_RECORD_ID_COLUMN] = original_id.map(lambda value: str(value))
    return out
