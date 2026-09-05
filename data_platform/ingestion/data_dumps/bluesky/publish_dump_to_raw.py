"""Copy Bluesky dump parquet Git LFS pointers into a pipeline raw run.

Run from the repo root:

    PYTHONPATH=. uv run python data_platform/ingestion/data_dumps/bluesky/publish_dump_to_raw.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

from data_platform.utils.config_paths import to_repo_relative
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from lib.constants import REPO_ROOT

DUMP_DATASET_ID = "bluesky_7e2c4a91-3b5f-4d8e-a6c1-0f9b8d2e5a73"
DUMP_DATASET_NAME = "jetstream_utc_day_2026_09_01"
DUMP_RAW_RUN_TIMESTAMP = "2026_09_01-00:00:00"
DUMP_PARQUET_ROOT = Path("data_platform/ingestion/data_dumps/bluesky/data/parquet")
DUMP_CONFIG_PATH = Path(
    "data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml"
)
DUMP_ROW_COUNT = 3_450_253
PARQUET_SUFFIX = ".parquet"


def _resolve_under_repo(path: Path) -> Path:
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def _source_parquet_root_label(parquet_root: Path) -> str:
    try:
        return to_repo_relative(parquet_root, REPO_ROOT)
    except ValueError:
        return parquet_root.as_posix()


def _list_parquet_files(parquet_root: Path) -> list[Path]:
    if not parquet_root.is_dir():
        raise FileNotFoundError(parquet_root)
    parquet_files = sorted(
        path for path in parquet_root.rglob(f"*{PARQUET_SUFFIX}") if path.is_file()
    )
    if not parquet_files:
        raise FileNotFoundError(parquet_root)
    return parquet_files


def _copy_parquet_files(
    parquet_files: list[Path],
    parquet_root: Path,
    run_dir: Path,
) -> None:
    for source_path in parquet_files:
        destination_path = run_dir / source_path.relative_to(parquet_root)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_path, destination_path)


def _write_dump_manifest(dataset_id: str, config_path: Path) -> None:
    write_dataset_manifest(
        "bluesky",
        dataset_id,
        name=DUMP_DATASET_NAME,
        ingestion_config=to_repo_relative(_resolve_under_repo(config_path), REPO_ROOT),
        data_format=ValidDataFormats.PARQUET,
    )


def _write_dump_run_metadata(
    run_dir: Path,
    dataset_id: str,
    raw_run_timestamp: str,
    parquet_root: Path,
) -> None:
    storage = BlueskyStorageManager(StorageStage.RAW, dataset_id)
    storage.write_run_metadata(
        run_dir,
        {
            "dataset_id": dataset_id,
            "sync_status": "completed",
            "sync_timestamp": raw_run_timestamp,
            "source": "jetstream_dump",
            "source_parquet_root": _source_parquet_root_label(parquet_root),
            "row_count": DUMP_ROW_COUNT,
        },
    )


def publish_dump_to_raw(
    parquet_root: Path,
    dataset_id: str,
    raw_run_timestamp: str,
    config_path: Path,
) -> Path:
    """Copy dump parquet files into a completed pipeline raw run.

    Parameters
    ----------
    parquet_root
        Hive-partitioned dump parquet directory.
    dataset_id
        Bluesky dataset id for the destination tree.
    raw_run_timestamp
        Destination raw run folder name.
    config_path
        Preprocess YAML recorded on the dataset manifest.

    Returns
    -------
    pathlib.Path
        Destination raw run directory.

    Raises
    ------
    FileNotFoundError
        When ``parquet_root`` is missing or contains no parquet files.
    FileExistsError
        When the destination raw run directory already exists.
    """
    resolved_root = _resolve_under_repo(parquet_root)
    parquet_files = _list_parquet_files(resolved_root)
    storage = BlueskyStorageManager(StorageStage.RAW, dataset_id)
    run_dir = storage.root_dir / raw_run_timestamp
    if run_dir.exists():
        raise FileExistsError(run_dir)
    run_dir.mkdir(parents=True)
    try:
        _copy_parquet_files(parquet_files, resolved_root, run_dir)
        _write_dump_manifest(dataset_id, config_path)
        _write_dump_run_metadata(run_dir, dataset_id, raw_run_timestamp, resolved_root)
    except Exception:
        shutil.rmtree(run_dir)
        raise
    return run_dir


def main() -> None:
    output_dir = publish_dump_to_raw(
        DUMP_PARQUET_ROOT,
        DUMP_DATASET_ID,
        DUMP_RAW_RUN_TIMESTAMP,
        DUMP_CONFIG_PATH,
    )
    print(output_dir)


if __name__ == "__main__":
    main()
