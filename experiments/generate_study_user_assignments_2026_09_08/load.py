"""Load remaining labels and join them to catalog cell membership.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore


def load_remaining_labels(
    path: str, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    raise NotImplementedError


def load_old_catalog_with_cells() -> pd.DataFrame:
    raise NotImplementedError


def load_new_catalog_with_cells(
    source: object, store: CampaignObjectStore, cache_dir: Path
) -> pd.DataFrame:
    raise NotImplementedError


def join_remaining_to_catalogs(
    remaining: pd.DataFrame, old_catalog: pd.DataFrame, new_catalog: pd.DataFrame
) -> pd.DataFrame:
    raise NotImplementedError


def write_shuffled_stimuli(joined: pd.DataFrame, experiment_dir: Path) -> Path:
    raise NotImplementedError
