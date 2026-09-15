"""Build the September three-group moderation cohort.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/reasoning_during_moderation_2026_09_15/shared/cohort.py --write-counts
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.reasoning_during_moderation_2026_09_15.shared.constants import (
    PAIR_ORDER_SEED,
)


def slim_trials(frame: pd.DataFrame) -> pd.DataFrame:
    """Keep linked-fate keep or remove moderation trials with a usable post id."""
    raise NotImplementedError


def assert_stable_pair_text(trials: pd.DataFrame) -> None:
    """Raise when a post has more than one original or mirror text."""
    raise NotImplementedError


def drop_conflicting_worker_posts(trials: pd.DataFrame) -> pd.DataFrame:
    """Drop worker-post pairs that contain both keep and remove."""
    raise NotImplementedError


def dedupe_worker_post(trials: pd.DataFrame) -> pd.DataFrame:
    """Keep the earliest row per worker and post."""
    raise NotImplementedError


def assign_group(keep_count: int, remove_count: int) -> str | None:
    """Return split, unanimous_keep, unanimous_remove, or None."""
    raise NotImplementedError


def pair_order_for_post(post_id: str, seed: int = PAIR_ORDER_SEED) -> tuple[str, str]:
    """Return a deterministic Post 1 and Post 2 role pair."""
    raise NotImplementedError


def build_cohort(trials: pd.DataFrame) -> pd.DataFrame:
    """Aggregate eligible posts into the three analysis groups."""
    raise NotImplementedError


def write_cohort(
    cohort: pd.DataFrame,
    slim: pd.DataFrame,
    metadata: dict[str, object],
    experiment_dir: Path,
) -> tuple[Path, Path, Path]:
    """Write cohort parquet, slim trials, and export metadata locally."""
    raise NotImplementedError


def upload_cohort(body: bytes, key: str, store: CampaignObjectStore) -> None:
    """Upload bytes with put_new and refuse an existing key."""
    raise NotImplementedError


def main() -> None:
    export = _download_export()
    trials = slim_trials(export)
    trials = drop_conflicting_worker_posts(trials)
    trials = dedupe_worker_post(trials)
    assert_stable_pair_text(trials)
    cohort = build_cohort(trials)
    _write_and_upload(cohort, trials)


def _download_export() -> pd.DataFrame:
    raise NotImplementedError


def _write_and_upload(cohort: pd.DataFrame, trials: pd.DataFrame) -> None:
    raise NotImplementedError


if __name__ == "__main__":
    main()
