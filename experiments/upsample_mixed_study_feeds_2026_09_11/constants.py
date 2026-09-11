"""Pinned counts and paths for the mixed-feed overprovisioned CSV.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UpsampleCounts:
    """Row counts produced by one upsample run."""


@dataclass(frozen=True)
class UpsampleRunResult:
    """Counts and paths from one overprovisioned CSV run."""
