"""Score separability labels against the gold presentation order.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


def score_labels(
    presentations: pd.DataFrame,
    store: CampaignObjectStore,
    experiment_dir: Path,
) -> Path:
    """Join labels to presentations, print tables, and write RESULTS.md."""
    raise NotImplementedError
