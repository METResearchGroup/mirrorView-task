"""Write the unused medium parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    UpsampleRunResult,
)


def write_upsampled_dataset(
    sampled: pd.DataFrame,
    leftover_left_medium: int,
    leftover_right_medium: int,
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> UpsampleRunResult:
    """Write local parquet, upload to S3, and write RESULTS.md.

    Parameters
    ----------
    sampled
        Sampled unused medium table.
    leftover_left_medium
        Leftover left-medium count before sampling.
    leftover_right_medium
        Leftover right-medium count before sampling.
    experiment_dir
        Folder that receives the parquet and RESULTS.md.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    UpsampleRunResult
        Local path, S3 URI, SHA-256, and counts.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    raise NotImplementedError


def print_run_summary(result: UpsampleRunResult) -> None:
    """Print row counts, leftover counts, S3 URI, and SHA-256."""
    raise NotImplementedError
