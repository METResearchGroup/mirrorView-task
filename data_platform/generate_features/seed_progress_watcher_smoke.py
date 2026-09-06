"""Temporary helper that seeds ``progress.jsonl`` and ``watcher.json`` under a disposable prefix.

Delete this file before the Step 7 PR merges.
"""

from __future__ import annotations

import typer

from data_platform.generate_features.feature_progress_watcher import resolve_feature_paths
from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore, FeaturePaths

DISPOSABLE_KEY_MARKER = "/_smoke/"
SEED_BATCH_SIZE = 2000


def seed_progress_and_watcher(
    store: CampaignObjectStore,
    paths: FeaturePaths,
    *,
    campaign_id: str,
    feature: str,
    durable_row_total: int,
) -> None:
    raise NotImplementedError


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str = typer.Option(..., "--smoke-prefix"),
    durable_row_total: int = typer.Option(..., "--durable-row-total"),
) -> None:
    paths = resolve_feature_paths(campaign_id, feature, smoke_prefix)
    store = CampaignObjectStore(paths.bucket)
    raise NotImplementedError


if __name__ == "__main__":
    typer.run(main)
