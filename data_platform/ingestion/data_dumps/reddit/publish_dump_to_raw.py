"""Copy Reddit dump parquet Git LFS pointers into pipeline raw runs.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/reddit/publish_dump_to_raw.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from data_platform.utils.config_paths import to_repo_relative
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import RedditStorageManager, StorageStage
from lib.constants import REPO_ROOT

DUMP_DATASET_ID = "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079"
DUMP_DATASET_NAME = "reddit-pushshift-dump-2025-05-06"
DUMP_CONFIG_PATH = Path(
    "data_platform/preprocessing/configs/reddit/pushshift_dump.yaml"
)
DUMP_SOURCE = "pushshift_dump"
DUMP_SOURCES: tuple[tuple[Path, str], ...] = (
    (
        Path("data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-05.parquet"),
        "2025_05_01-00:00:00",
    ),
    (
        Path("data_platform/ingestion/data_dumps/reddit/filtered/RC_2025-06.parquet"),
        "2025_06_01-00:00:00",
    ),
)
PARQUET_SUFFIX = ".parquet"
COMMENTS_PARQUET_FILENAME = "comments.parquet"


def _resolve_under_repo(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _stored_path(path: Path) -> str:
    try:
        return to_repo_relative(path, REPO_ROOT)
    except ValueError:
        return path.as_posix()


def _require_run_directory_name(raw_run: str) -> str:
    if not raw_run or raw_run in {".", ".."}:
        raise ValueError("dump raw_run must be a single directory name")
    candidate = Path(raw_run)
    if candidate.is_absolute() or len(candidate.parts) != 1:
        raise ValueError("dump raw_run must be a single directory name")
    if "/" in raw_run or "\\" in raw_run:
        raise ValueError("dump raw_run must be a single directory name")
    return raw_run


def _require_parquet_source(source_path: Path) -> Path:
    if source_path.suffix != PARQUET_SUFFIX:
        raise ValueError("dump source must be a parquet file")
    return source_path


def _require_unique_raw_runs(jobs: list[tuple[Path, str]]) -> None:
    raw_runs = [raw_run for _source_path, raw_run in jobs]
    if len(raw_runs) != len(set(raw_runs)):
        raise ValueError("dump sources must use unique raw_run names")


def _source_jobs(sources: list[tuple[Path, str]]) -> list[tuple[Path, str]]:
    if not sources:
        raise ValueError("dump sources must not be empty")
    jobs: list[tuple[Path, str]] = []
    for source_path, raw_run in sources:
        jobs.append(
            (
                _require_parquet_source(_resolve_under_repo(source_path)),
                _require_run_directory_name(raw_run),
            )
        )
    _require_unique_raw_runs(jobs)
    return jobs


def _write_dump_manifest(dataset_id: str, config_path: Path) -> None:
    write_dataset_manifest(
        "reddit",
        dataset_id,
        name=DUMP_DATASET_NAME,
        ingestion_config=to_repo_relative(_resolve_under_repo(config_path), REPO_ROOT),
        data_format=ValidDataFormats.PARQUET,
    )


def _write_dump_run_metadata(
    run_dir: Path,
    dataset_id: str,
    raw_run: str,
    source_path: Path,
) -> None:
    storage = RedditStorageManager(StorageStage.RAW, dataset_id)
    storage.write_run_metadata(
        run_dir,
        {
            "dataset_id": dataset_id,
            "sync_status": "completed",
            "sync_timestamp": raw_run,
            "source": DUMP_SOURCE,
            "source_dump_file": _stored_path(source_path),
        },
    )


def _copy_source_to_raw_run(
    source_path: Path,
    run_dir: Path,
) -> None:
    destination = run_dir / COMMENTS_PARQUET_FILENAME
    shutil.copy2(source_path, destination)


def publish_dump_to_raw(
    sources: list[tuple[Path, str]],
    dataset_id: str,
    config_path: Path,
) -> list[Path]:
    """Copy dump parquet files into completed pipeline raw runs.

    Parameters
    ----------
    sources
        Pairs of source parquet path and destination raw run folder name.
    dataset_id
        Reddit dataset id for the destination tree.
    config_path
        Preprocess YAML recorded on the dataset manifest.

    Returns
    -------
    list[pathlib.Path]
        Destination raw run directories, in source order.

    Raises
    ------
    FileNotFoundError
        When a source parquet file is missing.
    FileExistsError
        When a destination raw run directory already exists.
    ValueError
        When a source is not parquet, a raw run name is unsafe, or raw run
        names are duplicated.
    """
    jobs = _source_jobs(sources)
    for source_path, _raw_run in jobs:
        if not source_path.is_file():
            raise FileNotFoundError(source_path)
    storage = RedditStorageManager(StorageStage.RAW, dataset_id)
    planned_runs = [storage.root_dir / raw_run for _source_path, raw_run in jobs]
    for run_dir in planned_runs:
        if run_dir.exists():
            raise FileExistsError(run_dir)
    created: list[Path] = []
    try:
        _write_dump_manifest(dataset_id, config_path)
        for source_path, raw_run in jobs:
            run_dir = storage.root_dir / raw_run
            run_dir.mkdir(parents=True)
            created.append(run_dir)
            _copy_source_to_raw_run(source_path, run_dir)
            _write_dump_run_metadata(run_dir, dataset_id, raw_run, source_path)
    except Exception:
        for run_dir in created:
            shutil.rmtree(run_dir)
        raise
    return created


def main() -> None:
    output_dirs = publish_dump_to_raw(
        [(source_path, raw_run) for source_path, raw_run in DUMP_SOURCES],
        DUMP_DATASET_ID,
        DUMP_CONFIG_PATH,
    )
    for output_dir in output_dirs:
        print(output_dir)


if __name__ == "__main__":
    main()
