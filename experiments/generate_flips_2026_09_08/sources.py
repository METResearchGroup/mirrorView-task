"""Pinned filtered parquet and run constants for flip generation."""

from __future__ import annotations

from dataclasses import dataclass

OUTPUT_S3_BUCKET = "mirrorview-experimental-artifacts"


@dataclass(frozen=True)
class FilteredSource:
    """One pinned filtered parquet used as flip-generation input."""

    uri: str
    sha256: str
    expected_row_count: int


def pinned_filtered_source() -> FilteredSource:
    """Return the pinned filtered parquet identity."""
    raise NotImplementedError
