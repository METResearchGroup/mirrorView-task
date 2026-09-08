"""Write the sampled parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CleanupSummary,
    DATASET_FILENAME,
    FilterRunResult,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "filter_posts_used_for_stimulus_dataset_2026_09_08"
)


def write_local_parquet(sampled: pd.DataFrame, experiment_dir: Path) -> tuple[Path, bytes]:
    """Write ``dataset.parquet`` under the experiment folder and return its bytes.

    Parameters
    ----------
    sampled
        Sorted sampled stimulus table.
    experiment_dir
        Folder that receives ``dataset.parquet``.

    Returns
    -------
    tuple[Path, bytes]
        Local path and parquet bytes.
    """
    body = _parquet_bytes(sampled)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return path, body


def write_filtered_dataset(
    sampled: pd.DataFrame,
    cleaned: pd.DataFrame,
    summary: CleanupSummary,
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> FilterRunResult:
    """Write local parquet, upload to S3, and write RESULTS.md."""
    raise NotImplementedError


def print_run_summary(result: FilterRunResult) -> None:
    """Print row counts, URIs, SHA-256, and both crosstab tables."""
    raise NotImplementedError


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()
