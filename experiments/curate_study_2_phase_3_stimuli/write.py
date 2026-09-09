"""Write the catalog CSV, upload it, and write RESULTS.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.curate_study_2_phase_3_stimuli.sources import CatalogRunResult


def write_catalog(
    catalog: pd.DataFrame,
    available: dict[str, dict[str, int]],
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> CatalogRunResult:
    """Write local CSV, upload with put_new, and write RESULTS.md."""
    raise NotImplementedError


def write_pause_results(
    available: dict[str, dict[str, int]],
    experiment_dir: Path | None = None,
) -> CatalogRunResult:
    """Write RESULTS.md for a shortfall pause and do not upload CSV."""
    raise NotImplementedError


def print_run_summary(result: CatalogRunResult) -> None:
    """Print available counts and whether the catalog was written."""
    raise NotImplementedError
