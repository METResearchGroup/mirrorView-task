"""Write remaining label counts locally, upload to S3, and write RESULTS.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.constants import (
    LabelCountRunResult,
    NewCatalogSource,
)


def write_required_label_counts(
    counts: pd.DataFrame,
    source: NewCatalogSource,
    experiment_dir: Path,
    store: CampaignObjectStore,
    old_catalog_ids: int,
) -> LabelCountRunResult:
    """Write the local CSV, upload it, and write RESULTS.md."""
    raise NotImplementedError


def print_run_summary(result: LabelCountRunResult) -> None:
    """Print remaining label totals and the S3 URI."""
    raise NotImplementedError
