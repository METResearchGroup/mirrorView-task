"""Preprocess Bluesky posts from raw CSV storage to filtered preprocessed output.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \\
        --dataset-id bluesky_<uuid>

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_bluesky.py \\
        --config data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml
"""

from __future__ import annotations

from pathlib import Path

import typer

from data_platform.models.sync import SyncBlueskyPostModel
from data_platform.preprocessing.runner import (
    PreprocessPlatformSpec,
    TextValidator,
)
from data_platform.preprocessing.runner import (
    preprocess_records as run_preprocess_records,
)
from data_platform.preprocessing.truncate_long_text import truncate_long_text
from data_platform.preprocessing.validators.bluesky_validators import (
    check_if_valid_post_length,
)
from data_platform.preprocessing.validators.validators import (
    check_if_not_phone,
    check_if_post_has_no_urls,
    check_if_text_english,
)
from data_platform.utils.config_paths import load_yaml_config, resolve_config_path
from data_platform.utils.platform_specific_columns import BLUESKY_COLUMNS
from data_platform.utils.storage import BlueskyStorageManager
from lib.constants import REPO_ROOT

POST_TEXT_VALIDATORS: tuple[TextValidator, ...] = (
    check_if_not_phone,
    check_if_valid_post_length,
    check_if_post_has_no_urls,
    check_if_text_english,
)

BLUESKY_SPEC = PreprocessPlatformSpec(
    platform="bluesky",
    storage_cls=BlueskyStorageManager,
    model_cls=SyncBlueskyPostModel,
    columns=BLUESKY_COLUMNS,
    text_validators=POST_TEXT_VALIDATORS,
    author_handle_source_column="author_handle",
    text_transforms=(truncate_long_text,),
)


def preprocess_records(
    dataset_id: str,
    sample_size: int | None = None,
) -> Path:
    """Run Bluesky preprocess, optionally sampling kept rows before write.

    Parameters
    ----------
    dataset_id
        Dataset identifier from ingestion or dump YAML.
    sample_size
        Maximum kept rows to write. ``None`` writes every kept row.

    Returns
    -------
    pathlib.Path
        Path to the new preprocessed run directory.
    """
    return run_preprocess_records(
        dataset_id,
        BLUESKY_SPEC,
        sample_size,
    )


def _require_dataset_id_or_config(dataset_id: str | None, config: Path | None) -> None:
    if dataset_id is None and config is None:
        raise typer.BadParameter("Provide --dataset-id or --config")
    if dataset_id is not None and config is not None:
        raise typer.BadParameter("Provide --dataset-id or --config, not both")


def _sample_size_from_yaml(config_values: dict) -> int | None:
    params = config_values.get("preprocessing_params")
    if not isinstance(params, dict):
        return None
    sample_size = params.get("sample_size")
    return int(sample_size) if sample_size is not None else None


def _resolve_preprocess_cli(
    dataset_id: str | None,
    config: Path | None,
    sample_size: int | None,
) -> tuple[str, int | None]:
    _require_dataset_id_or_config(dataset_id, config)
    if config is None:
        return str(dataset_id), sample_size
    config_path = resolve_config_path(config, REPO_ROOT)
    config_values = load_yaml_config(config_path)
    yaml_sample_size = _sample_size_from_yaml(config_values)
    resolved_sample_size = yaml_sample_size if sample_size is None else sample_size
    return str(config_values["dataset_id"]), resolved_sample_size


def main(
    dataset_id: str | None = typer.Option(
        None,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (bluesky_<uuid>)",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Dump or preprocess YAML with dataset_id and sample settings",
    ),
    sample_size: int | None = typer.Option(
        None,
        "--sample-size",
        help="Override YAML sample size; omit to write every kept row",
    ),
) -> None:
    resolved_dataset_id, resolved_sample_size = _resolve_preprocess_cli(
        dataset_id, config, sample_size
    )
    preprocess_records(resolved_dataset_id, resolved_sample_size)


if __name__ == "__main__":
    typer.run(main)
