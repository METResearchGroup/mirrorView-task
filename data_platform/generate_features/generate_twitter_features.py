"""Generate features for preprocessed Twitter posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_twitter_features.py \\
        --dataset-id twitter_<uuid> --batch-size 64
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_config,
    features_from_cli,
    generate_platform_features,
    load_preprocessed_records,
)
from data_platform.models.sync import SyncTwitterPostModel
from data_platform.utils.platform_specific_columns import TWITTER_COLUMNS
from data_platform.utils.storage import TwitterStorageManager

TWITTER_SPEC = FeaturePlatformSpec(
    platform="twitter",
    storage_cls=TwitterStorageManager,
    model_cls=SyncTwitterPostModel,
    columns=TWITTER_COLUMNS,
    empty_message="generate_twitter_features: no preprocessed posts found",
)


def twitter_feature_config(*args, **kwargs):
    return build_feature_config(TWITTER_SPEC, *args, **kwargs)


def load_posts(dataset_id: str):
    return load_preprocessed_records(TWITTER_SPEC, dataset_id)


def generate_twitter_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    opik_enabled: bool = False,
    feature_subset: list[str] | None = None,
    run_dir_name: str | None = None,
) -> dict[str, Path]:
    """Load Twitter posts and generate the requested feature labels."""
    return generate_platform_features(
        TWITTER_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        opik_enabled=opik_enabled,
        feature_subset=feature_subset,
        run_dir_name=run_dir_name,
    )


def main(
    dataset_id: str = typer.Option(
        ...,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (twitter_<uuid>)",
    ),
    batch_size: int = typer.Option(64, "--batch-size"),
    max_concurrency: int = typer.Option(80, "--max-concurrency"),
    opik_enabled: bool = typer.Option(False, "--opik", help="Enable Opik telemetry"),
    features: list[str] | None = typer.Option(
        None,
        "--features",
        help="Feature name(s); repeat the flag per feature, e.g. --features is_political",
    ),
    run_dir: str | None = typer.Option(
        None,
        "--run-dir",
        help="Feature run timestamp to resume (e.g. 2026_05_30-12:00:00)",
    ),
) -> None:
    """CLI entrypoint for resumable Twitter feature generation."""
    generate_twitter_features(
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        opik_enabled=opik_enabled,
        feature_subset=features_from_cli(features),
        run_dir_name=run_dir,
    )


if __name__ == "__main__":
    typer.run(main)
