"""Filter Reddit comments from a raw run and write the comments that pass.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \\
        --dataset-id reddit_<uuid>

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \\
        --config data_platform/preprocessing/configs/reddit/pushshift_dump.yaml
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import typer

from data_platform.models.sync import SyncRedditCommentModel
from data_platform.preprocessing.runner import (
    PreprocessPlatformSpec,
    RowValidator,
    TextValidator,
)
from data_platform.preprocessing.runner import (
    passes_all_validators as _passes_all_validators,
)
from data_platform.preprocessing.runner import (
    passes_row_validators as _passes_row_validators,
)
from data_platform.preprocessing.runner import (
    preprocess_records as run_preprocess_records,
)
from data_platform.preprocessing.sample import MIN_SAMPLE_SIZE
from data_platform.preprocessing.truncate_long_text import truncate_long_text
from data_platform.preprocessing.validators.reddit_validators import (
    check_if_body_not_removed,
    check_if_no_direct_urls,
    check_if_no_markdown_links,
    check_if_no_media_hosts,
    check_if_no_reddit_mentions,
    check_if_not_automoderator,
    check_if_valid_reddit_comment_min_length,
)
from data_platform.preprocessing.validators.validators import (
    check_if_not_phone,
    check_if_text_english,
)
from data_platform.utils.config_paths import load_yaml_config, resolve_config_path
from data_platform.utils.platform_specific_columns import (
    REDDIT_COLUMNS,
    REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN,
)
from data_platform.utils.storage import RedditStorageManager
from lib.constants import REPO_ROOT

COMMENT_TEXT_VALIDATORS: tuple[TextValidator, ...] = (
    check_if_body_not_removed,
    check_if_valid_reddit_comment_min_length,
    check_if_no_reddit_mentions,
    check_if_no_markdown_links,
    check_if_no_direct_urls,
    check_if_no_media_hosts,
    check_if_not_phone,
    check_if_text_english,
)

COMMENT_ROW_VALIDATORS: tuple[RowValidator, ...] = (check_if_not_automoderator,)

REDDIT_SPEC = PreprocessPlatformSpec(
    platform="reddit",
    storage_cls=RedditStorageManager,
    model_cls=SyncRedditCommentModel,
    columns=REDDIT_COLUMNS,
    text_validators=COMMENT_TEXT_VALIDATORS,
    row_validators=COMMENT_ROW_VALIDATORS,
    original_platform_text_column=REDDIT_ORIGINAL_PLATFORM_TEXT_COLUMN,
    author_handle_source_column="author",
    text_transforms=(truncate_long_text,),
)


def passes_all_validators(
    text: str,
    validators: Sequence[TextValidator] = COMMENT_TEXT_VALIDATORS,
) -> bool:
    return _passes_all_validators(text, validators)


def passes_row_validators(
    author: str,
    validators: Sequence[RowValidator] = COMMENT_ROW_VALIDATORS,
) -> bool:
    return _passes_row_validators(author, validators)


def preprocess_records(
    dataset_id: str,
    sample_size: int | None = None,
) -> Path:
    """Run Reddit preprocess, optionally sampling kept rows before write.

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
        REDDIT_SPEC,
        sample_size,
    )


def _require_dataset_id_or_config(dataset_id: str | None, config: Path | None) -> None:
    if dataset_id is None and config is None:
        raise typer.BadParameter("Provide --dataset-id or --config")
    if dataset_id is not None and config is not None:
        raise typer.BadParameter("Provide --dataset-id or --config, not both")


def _sample_size_from_yaml(config_values: dict) -> int:
    params = config_values.get("preprocessing_params")
    if not isinstance(params, dict) or params.get("sample_size") is None:
        raise typer.BadParameter(
            "Config preprocessing_params.sample_size is required"
        )
    sample_size = params["sample_size"]
    if (
        isinstance(sample_size, bool)
        or not isinstance(sample_size, int)
        or sample_size < MIN_SAMPLE_SIZE
    ):
        raise typer.BadParameter(
            "Config preprocessing_params.sample_size must be a positive integer"
        )
    return sample_size


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
        help="Dataset identifier from ingestion YAML (reddit_<uuid>)",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Dump or preprocess YAML with dataset_id and sample settings",
    ),
    sample_size: int | None = typer.Option(
        None,
        "--sample-size",
        help="Override YAML sample size",
    ),
) -> None:
    resolved_dataset_id, resolved_sample_size = _resolve_preprocess_cli(
        dataset_id, config, sample_size
    )
    preprocess_records(resolved_dataset_id, resolved_sample_size)


if __name__ == "__main__":
    typer.run(main)
