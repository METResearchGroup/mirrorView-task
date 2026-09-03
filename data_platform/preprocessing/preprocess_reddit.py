"""Filter Reddit comments from a raw run and write the comments that pass.

Run from the repo root. Pass ``--dataset-id`` to read a live dataset and write
every comment that passes the filters.

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \\
        --dataset-id reddit_<uuid>

Pass ``--config`` with the dump YAML to read parquet raw runs and keep at most
200,000 comments that pass the filters per month file.

    PYTHONPATH=. uv run python data_platform/preprocessing/preprocess_reddit.py \\
        --config data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import typer

from data_platform.ingestion.sync_checkpoint import require_dataset_id
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
from data_platform.preprocessing.sample_records import MIN_SAMPLE_SIZE
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
)

PREPROCESS_KEY = "preprocess"
SAMPLE_SIZE_KEY = "sample_size"
SAMPLE_SEED_KEY = "sample_seed"


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


def load_dump_preprocess_settings(config_path: Path) -> tuple[str, int, int]:
    """Read dataset id and sample settings from a dump preprocess YAML.

    Parameters
    ----------
    config_path
        Absolute path to the dump YAML.

    Returns
    -------
    tuple[str, int, int]
        ``dataset_id``, ``sample_size``, and ``sample_seed``.

    Raises
    ------
    FileNotFoundError
        When the YAML file does not exist.
    ValueError
        When required keys are missing or ``sample_size`` is less than 1.
    """
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config = load_yaml_config(config_path)
    dataset_id = require_dataset_id(config, platform="reddit")
    preprocess = config.get(PREPROCESS_KEY)
    if not isinstance(preprocess, dict):
        raise ValueError("dump config must include preprocess")
    sample_size = preprocess.get(SAMPLE_SIZE_KEY)
    sample_seed = preprocess.get(SAMPLE_SEED_KEY)
    if not isinstance(sample_size, int) or sample_size < MIN_SAMPLE_SIZE:
        raise ValueError("sample_size must be at least 1")
    if not isinstance(sample_seed, int):
        raise ValueError("sample_seed must be an int")
    return dataset_id, sample_size, sample_seed


def preprocess_records(
    dataset_id: str,
    sample_size: int | None = None,
    sample_seed: int | None = None,
) -> Path:
    return run_preprocess_records(
        dataset_id,
        REDDIT_SPEC,
        sample_size,
        sample_seed,
    )


def main(
    dataset_id: str | None = typer.Option(
        None,
        "--dataset-id",
        help="Dataset identifier from ingestion YAML (reddit_<uuid>)",
    ),
    config: Path | None = typer.Option(
        None,
        "--config",
        help="Dump dataset YAML with dataset_id and preprocess sample settings",
    ),
) -> None:
    if config is not None and dataset_id is not None:
        raise typer.BadParameter("Pass only one of --config or --dataset-id")
    if config is None and dataset_id is None:
        raise typer.BadParameter("Pass --config or --dataset-id")
    if config is not None:
        config_path = resolve_config_path(config, REPO_ROOT)
        resolved_dataset_id, sample_size, sample_seed = load_dump_preprocess_settings(
            config_path
        )
        preprocess_records(resolved_dataset_id, sample_size, sample_seed)
        return
    preprocess_records(dataset_id)


if __name__ == "__main__":
    typer.run(main)
