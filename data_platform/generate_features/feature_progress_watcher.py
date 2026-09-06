"""Short restartable watcher that prints a rolling progress comment for one campaign feature."""

from __future__ import annotations

import typer

from data_platform.generate_features.progress_record import ProgressRecord
from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    FeaturePaths,
)

MILESTONE_ROWS = 10_000


def resolve_feature_paths(
    campaign_id: str, feature: str, smoke_prefix: str | None
) -> FeaturePaths:
    raise NotImplementedError


def run_watcher_once(store: CampaignObjectStore, paths: FeaturePaths) -> None:
    raise NotImplementedError


def main(
    campaign_id: str = typer.Option(..., "--campaign-id"),
    feature: str = typer.Option(..., "--feature"),
    smoke_prefix: str | None = typer.Option(None, "--smoke-prefix"),
    dry_render: bool = typer.Option(False, "--dry-render"),
    once: bool = typer.Option(False, "--once"),
) -> None:
    paths = resolve_feature_paths(campaign_id, feature, smoke_prefix)
    store = CampaignObjectStore(paths.bucket)
    run_watcher_once(store, paths)


if __name__ == "__main__":
    typer.run(main)
