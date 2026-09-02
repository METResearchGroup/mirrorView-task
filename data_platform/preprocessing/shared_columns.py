"""Shared column helpers used across platform preprocessing pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pandas as pd

from data_platform.utils.platform_specific_columns import CANONICAL_AUTHOR_HANDLE_COLUMN

if TYPE_CHECKING:
    from data_platform.preprocessing.runner import PreprocessPlatformSpec


def add_canonical_author_columns(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Copy the platform author-handle source column onto shared ``author_handle``.

    Each platform names the handle differently in raw storage: Reddit uses
    ``author``, Twitter uses ``username``, and Bluesky already stores
    ``author_handle``. Downstream preprocessing, features, and curation read
    one column—``author_handle``—so this helper copies from the platform-specific
    source named on the spec and overwrites any existing ``author_handle`` value.

    Original platform columns (for example Reddit ``author`` or Twitter
    ``username``) are left unchanged. ``author_id`` is not added or modified.

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
    out[CANONICAL_AUTHOR_HANDLE_COLUMN] = original_handle.map(lambda value: str(value))
    return out
