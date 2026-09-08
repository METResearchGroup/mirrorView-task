"""Write the sampled parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.combine_data_into_stimulus_set_2026_09_08.crosstab import (
    stance_by_toxicity,
    stance_by_toxicity_by_integration,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CleanupSummary,
    FilterRunResult,
)


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
