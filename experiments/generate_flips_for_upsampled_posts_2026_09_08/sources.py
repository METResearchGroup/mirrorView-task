"""Pinned unified upsample parquet and flip-run constants."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnifiedSource:
    """One pinned unified upsample parquet used as flip-generation input."""

    s3_uri: str
    sha256: str
    expected_row_count: int


@dataclass(frozen=True)
class NamedFlipCopyResult:
    """Named sibling copy of the concatenated flips parquet."""

    s3_uri: str
    sha256: str


def pinned_unified_source() -> UnifiedSource:
    """Return the pinned unified 2,300 post parquet identity."""
    raise NotImplementedError
