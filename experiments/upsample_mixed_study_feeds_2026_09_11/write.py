"""Write the overprovisioned source CSV and local party files.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    UpsampleRunResult,
)


def write_overprovisioned_batch(
    source_rows: list[AssignmentRow],
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    experiment_dir: Path,
) -> UpsampleRunResult:
    """Write the overprovisioned source CSV, party files, catalog, and config.

    Raises
    ------
    ValueError
        When party counts do not match the pinned totals.
    """
    raise NotImplementedError


def upload_overprovisioned_csv(store: CampaignObjectStore, body: bytes) -> None:
    """Upload the overprovisioned CSV with ``put_new``.

    Raises
    ------
    FileExistsError
        When the experimental key already exists.
    """
    raise NotImplementedError


def write_results_md(result: UpsampleRunResult, experiment_dir: Path) -> Path:
    """Write ``RESULTS.md`` for one live run."""
    raise NotImplementedError
