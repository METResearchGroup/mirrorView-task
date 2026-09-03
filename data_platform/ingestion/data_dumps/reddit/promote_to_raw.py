"""Copy dump parquet Git LFS pointers into pipeline raw runs.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/promote_to_raw.py
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from data_platform.ingestion.sync_checkpoint import require_dataset_id
from data_platform.utils.config_paths import load_yaml_config, to_repo_relative
from data_platform.utils.dataset import (
    MANIFEST_FILENAME,
    ValidDataFormats,
    dataset_root,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp

DUMP_DATASET_CONFIG = Path(
    "data_platform/ingestion/data_dumps/reddit/pushshift_dump.yaml"
)
COMMENTS_PARQUET_FILENAME = "comments.parquet"
METADATA_FILENAME = "metadata.json"
SYNC_STATUS_COMPLETED = "completed"
PLATFORM_REDDIT = "reddit"
RAW_STAGE = "raw"
INGESTION_CONFIG_KEY = "ingestion_config"
SOURCE_DUMP_FILE_KEY = "source_dump_file"
SYNC_STATUS_KEY = "sync_status"
DATASET_ID_KEY = "dataset_id"
SOURCES_KEY = "sources"
SOURCE_PARQUET_KEY = "parquet"
SOURCE_RAW_RUN_KEY = "raw_run"
NAME_KEY = "name"
OUTPUT_FORMAT_KEY = "output_format"
MANIFEST_FORMAT_KEY = "format"
MANIFEST_PLATFORM_KEY = "platform"
MANIFEST_NAME_KEY = "name"
MANIFEST_CREATED_AT_KEY = "created_at"


def _resolve_dataset_root(dataset_id: str, data_root: Path | None) -> Path:
    if data_root is None:
        return dataset_root(PLATFORM_REDDIT, dataset_id)
    return data_root / PLATFORM_REDDIT / dataset_id


def _resolve_source_path(raw_path: str) -> Path:
    candidate = Path(raw_path)
    if candidate.is_absolute():
        return candidate
    return REPO_ROOT / candidate


def _stored_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return to_repo_relative(resolved, REPO_ROOT)
    except ValueError:
        return resolved.as_posix()


def _source_jobs(config: dict[str, Any]) -> list[tuple[Path, str]]:
    sources = config.get(SOURCES_KEY)
    if not isinstance(sources, list) or not sources:
        raise ValueError("dump config must include sources")
    jobs: list[tuple[Path, str]] = []
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("dump config sources must be mappings")
        jobs.append(
            (
                _resolve_source_path(str(source[SOURCE_PARQUET_KEY])),
                str(source[SOURCE_RAW_RUN_KEY]),
            )
        )
    return jobs


def _require_sources_and_destinations(
    jobs: list[tuple[Path, str]],
    dataset_dir: Path,
) -> None:
    for source_path, _raw_run in jobs:
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
    for source_path, raw_run in jobs:
        destination = (
            dataset_dir / RAW_STAGE / raw_run / COMMENTS_PARQUET_FILENAME
        )
        if destination.exists():
            raise FileExistsError(destination)


def _write_dataset_manifest(
    dataset_dir: Path,
    dataset_id: str,
    name: str,
    ingestion_config: str,
    data_format: ValidDataFormats,
) -> None:
    dataset_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        DATASET_ID_KEY: dataset_id,
        MANIFEST_PLATFORM_KEY: PLATFORM_REDDIT,
        MANIFEST_NAME_KEY: name,
        MANIFEST_CREATED_AT_KEY: get_current_timestamp(),
        INGESTION_CONFIG_KEY: ingestion_config,
        MANIFEST_FORMAT_KEY: data_format.value,
    }
    (dataset_dir / MANIFEST_FILENAME).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8",
    )


def _copy_source_to_raw_run(
    source_path: Path,
    dataset_dir: Path,
    raw_run: str,
    dataset_id: str,
    ingestion_config: str,
) -> None:
    run_dir = dataset_dir / RAW_STAGE / raw_run
    run_dir.mkdir(parents=True, exist_ok=True)
    destination = run_dir / COMMENTS_PARQUET_FILENAME
    shutil.copy2(source_path, destination)
    metadata = {
        DATASET_ID_KEY: dataset_id,
        SYNC_STATUS_KEY: SYNC_STATUS_COMPLETED,
        INGESTION_CONFIG_KEY: ingestion_config,
        SOURCE_DUMP_FILE_KEY: _stored_path(source_path),
    }
    (run_dir / METADATA_FILENAME).write_text(
        json.dumps(metadata, indent=2),
        encoding="utf-8",
    )


def promote_dump_sources_to_raw(
    config_path: Path,
    data_root: Path | None,
) -> Path:
    """Copy each dump parquet pointer into a completed raw run for the dump dataset.

    Parameters
    ----------
    config_path
        Dump dataset YAML. Must include ``dataset_id`` and ``sources``.
    data_root
        Optional data-platform data directory for tests. ``None`` uses the
        package data root.

    Returns
    -------
    pathlib.Path
        Dataset root that contains ``dataset.json`` and ``raw/``.

    Raises
    ------
    FileNotFoundError
        When the YAML or a source parquet file is missing.
    FileExistsError
        When a destination ``comments.parquet`` already exists.
    ValueError
        When ``dataset_id`` is missing or malformed.
    """
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    config = load_yaml_config(config_path)
    dataset_id = require_dataset_id(config, platform=PLATFORM_REDDIT)
    dataset_dir = _resolve_dataset_root(dataset_id, data_root)
    jobs = _source_jobs(config)
    _require_sources_and_destinations(jobs, dataset_dir)
    ingestion_config = _stored_path(config_path)
    output_format = ValidDataFormats(config.get(OUTPUT_FORMAT_KEY, "csv"))
    _write_dataset_manifest(
        dataset_dir,
        dataset_id,
        str(config[NAME_KEY]),
        ingestion_config,
        output_format,
    )
    for source_path, raw_run in jobs:
        _copy_source_to_raw_run(
            source_path,
            dataset_dir,
            raw_run,
            dataset_id,
            ingestion_config,
        )
    return dataset_dir


def main(argv: list[str] | None = None) -> None:
    """Promote dump parquet pointers using the dump dataset YAML.

    Parameters
    ----------
    argv
        Argument list without the program name. ``None`` reads ``sys.argv``.
    """
    parser = argparse.ArgumentParser(
        description="Copy Reddit dump parquet pointers into pipeline raw runs."
    )
    parser.add_argument("--config", type=Path, default=DUMP_DATASET_CONFIG)
    args = parser.parse_args(argv)
    promote_dump_sources_to_raw(args.config, None)


if __name__ == "__main__":
    main()
