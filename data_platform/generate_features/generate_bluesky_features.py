"""Generate features for preprocessed Bluesky posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --batch-size 64
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.models import FeatureRunConfig
from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_config,
    features_from_cli,
    generate_feature_subset,
    load_preprocessed_records,
    run_feature_generation,
)
from data_platform.models.sync import SyncBlueskyPostModel
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.gate_checks import require_all_runs_complete
from data_platform.utils.platform_ids import BLUESKY_BINDING
from data_platform.utils.storage import BlueskyStorageManager, StorageStage

BLUESKY_SPEC = FeaturePlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    model_cls=SyncBlueskyPostModel,
    binding=BLUESKY_BINDING,
    empty_message="generate_bluesky_features: no preprocessed posts found",
    require_all_runs_complete=True,
)


def load_all_posts(dataset_id: str):
    return load_preprocessed_records(BLUESKY_SPEC, dataset_id)


def generate_bluesky_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    opik_enabled: bool = False,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Load Bluesky posts and generate the requested feature labels."""
    dataset_id = validate_dataset_id(dataset_id)

    preprocessed_storage = BlueskyStorageManager(StorageStage.PREPROCESSED, dataset_id)
    if preprocessed_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No preprocessed runs found for dataset {dataset_id}")
    require_all_runs_complete(preprocessed_storage, dataset_id)

    features_subset = generate_feature_subset(feature_subset)
    run_config = FeatureRunConfig(
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        opik_enabled=opik_enabled,
    )
    posts = load_all_posts(dataset_id)
    config = build_feature_config(
        BLUESKY_SPEC,
        dataset_id,
        run_config=run_config,
        features_subset=features_subset,
    )
    return run_feature_generation(posts, config, empty_message=BLUESKY_SPEC.empty_message)


def main(
    dataset_id: str = typer.Option(
        ...,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (bluesky_<uuid>)",
    ),
    batch_size: int = typer.Option(64, "--batch-size"),
    max_concurrency: int = typer.Option(80, "--max-concurrency"),
    opik_enabled: bool = typer.Option(False, "--opik", help="Enable Opik telemetry"),
    features: list[str] | None = typer.Option(
        None,
        "--features",
        help="Feature name(s); repeat the flag per feature, e.g. --features is_political",
    ),
) -> None:
    """CLI entrypoint for resumable Bluesky feature generation."""
    generate_bluesky_features(
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        opik_enabled=opik_enabled,
        feature_subset=features_from_cli(features),
    )


if __name__ == "__main__":
    typer.run(main)
