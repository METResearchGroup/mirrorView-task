"""Pinned unified upsample parquet and flip-run constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedSource:
    """One pinned unified upsample parquet used as flip-generation input."""

    s3_uri: str
    sha256: str
    expected_row_count: int


def pinned_unified_source() -> UnifiedSource:
    """Return the pinned unified 2,300 post parquet identity."""
    raise NotImplementedError
