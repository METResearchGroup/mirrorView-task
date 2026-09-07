"""Generate features for preprocessed Bluesky posts.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --batch-size 64

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --checkpoint 2026_05_30-12:00:00

Campaign mode writes immutable 2,000-row batch objects to S3 and resumes from
that prefix on restart:

    PYTHONPATH=. uv run python data_platform/generate_features/generate_bluesky_features.py \\
        --dataset-id bluesky_<uuid> --preprocessed-run 2026_09_03-23:51:30 \\
        --campaign-id bluesky_2026_09_03_235130_llm_features_v1 \\
        --features is_news_or_opinion --batch-size 2000
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.generate_features.platform_cli import (
    FeaturePlatformSpec,
    build_feature_cli_app,
    build_feature_cli_main,
    generate_platform_campaign_feature,
    generate_platform_features,
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
)

_DATASET_ID_HELP = "Dataset identifier from ingestion YAML (bluesky_<uuid>)"
app = build_feature_cli_app(BLUESKY_SPEC, _DATASET_ID_HELP)
main = build_feature_cli_main(BLUESKY_SPEC, _DATASET_ID_HELP)


def generate_bluesky_features(
    dataset_id: str,
    *,
    batch_size: int = 64,
    max_concurrency: int = 80,
    feature_subset: list[str] | None = None,
    checkpoint: str | None = None,
    campaign_id: str | None = None,
    preprocessed_run: str | None = None,
) -> dict[str, Path | str]:
    """Generate Bluesky feature labels in a new or unfinished feature run, or in S3 campaign mode.

    Parameters
    ----------
    dataset_id
        Dataset identifier from ingestion YAML.
    batch_size
        Label batch size. Campaign mode requires 2000.
    max_concurrency
        Engine concurrency cap.
    feature_subset
        Optional registry subset. None runs every feature. Campaign mode
        requires exactly one feature.
    checkpoint
        Named unfinished feature run timestamp. Pass None to start a new
        feature run. Not allowed in campaign mode.
    campaign_id
        S3 campaign id. Pass together with ``preprocessed_run`` to write
        immutable batch objects under the campaign feature prefix and resume
        from that prefix.
    preprocessed_run
        Preprocessed run timestamp that campaign mode labels.

    Returns
    -------
    dict[str, Path | str]
        Feature name to the label file written in the feature run folder, or
        to the S3 feature prefix URI in campaign mode.
    """
    if campaign_id is not None or preprocessed_run is not None:
        feature_names = feature_subset or []
        prefix_uri = generate_platform_campaign_feature(
            BLUESKY_SPEC,
            dataset_id,
            campaign_id=campaign_id,
            preprocessed_run=preprocessed_run,
            feature_subset=feature_subset,
            batch_size=batch_size,
            checkpoint=checkpoint,
        )
        return {feature_names[0]: prefix_uri}
    return generate_platform_features(
        BLUESKY_SPEC,
        dataset_id,
        batch_size=batch_size,
        max_concurrency=max_concurrency,
        feature_subset=feature_subset,
        checkpoint=checkpoint,
    )


if __name__ == "__main__":
    typer.run(main)
