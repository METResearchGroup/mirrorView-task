"""Upload the shared presentation parquet to S3.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    PresentationWriteResult,
)


def require_presentation_key_absent(store: CampaignObjectStore) -> None:
    """Raise FileExistsError when the presentation S3 key already exists."""
    raise NotImplementedError


def upload_presentation(
    presentations: pd.DataFrame,
    experiment_dir: Path,
    store: CampaignObjectStore,
) -> PresentationWriteResult:
    """Write local parquet, upload with put_new, and return the digest."""
    raise NotImplementedError


def print_presentation_summary(result: PresentationWriteResult) -> None:
    """Print the presentation row count and SHA-256."""
    raise NotImplementedError
