"""Generate features for preprocessed Bluesky posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        new-run --dataset-id bluesky_<uuid> --batch-size 64

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        resume --dataset-id bluesky_<uuid> --checkpoint 2026_05_30-12:00:00

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        resume --dataset-id bluesky_<uuid> --latest
"""

from __future__ import annotations

from pathlib import Path

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_cli_app,
    generate_platform_features,
    generate_platform_features_from_checkpoint,
)
from data_platform.models.sync import PreprocessedBlueskyPostModel
from data_platform.utils.platform_specific_columns import BLUESKY_COLUMNS
from data_platform.utils.storage import BlueskyStorageManager

BLUESKY_SPEC = FeaturePlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    model_cls=PreprocessedBlueskyPostModel,
    columns=BLUESKY_COLUMNS,
    empty_message="generate_bluesky_features: no preprocessed posts found",
    require_all_runs_complete=True,
)

app = build_feature_cli_app(
    BLUESKY_SPEC,
    "Dataset identifier from ingestion YAML (bluesky_<uuid>)",
)


def generate_bluesky_features(
    dataset_id: str,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Start a new Bluesky feature run and generate the requested labels."""
    return generate_platform_features(
        BLUESKY_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
    )


def generate_bluesky_features_from_checkpoint(
    dataset_id: str,
    checkpoint: str | None,
    latest: bool,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
) -> dict[str, Path]:
    """Resume an unfinished Bluesky feature run."""
    return generate_platform_features_from_checkpoint(
        BLUESKY_SPEC,
        dataset_id,
        checkpoint,
        latest,
        batch_size,
        max_concurrency,
        feature_subset,
    )


def main() -> None:
    """CLI entrypoint. Requires new-run or resume."""
    app()


if __name__ == "__main__":
    main()
