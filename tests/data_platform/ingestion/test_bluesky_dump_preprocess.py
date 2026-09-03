from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from data_platform.ingestion.data_dumps.bluesky.publish_dump_to_raw import (
    DUMP_CONFIG_PATH,
    DUMP_DATASET_ID,
    DUMP_RAW_RUN_TIMESTAMP,
    publish_dump_to_raw,
)
from data_platform.utils.dataset import MANIFEST_FILENAME
from data_platform.utils.storage import METADATA_FILENAME
from lib.constants import REPO_ROOT

def _expected_source_root(parquet_root: Path) -> str:
    resolved = parquet_root.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return resolved.as_posix()


HOUR_00 = Path("date=2026-09-01") / "hour=00" / "aaa.parquet"
HOUR_01 = Path("date=2026-09-01") / "hour=01" / "bbb.parquet"
EXPECTED_ROW_COUNT = 3450253
EXPECTED_SAMPLE_SIZE = 200000
EXPECTED_SAMPLE_SEED = 20260901


def _write_hive_parquet(parquet_root: Path) -> tuple[Path, Path]:
    first_path = parquet_root / HOUR_00
    second_path = parquet_root / HOUR_01
    first_path.parent.mkdir(parents=True)
    second_path.parent.mkdir(parents=True)
    first_path.write_bytes(b"pointer-a")
    second_path.write_bytes(b"pointer-b")
    return first_path, second_path


class TestPublishDumpToRaw:
    """Tests for publish_dump_to_raw()."""

    def test_copies_hive_parquet_and_writes_manifest(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Copies parquet bytes and writes dataset.json plus completed metadata."""
        parquet_root = tmp_path / "parquet"
        first_path, second_path = _write_hive_parquet(parquet_root)
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        result = publish_dump_to_raw(
            parquet_root,
            DUMP_DATASET_ID,
            DUMP_RAW_RUN_TIMESTAMP,
            config_path,
        )

        expected_run_dir = (
            data_root / "bluesky" / DUMP_DATASET_ID / "raw" / DUMP_RAW_RUN_TIMESTAMP
        )
        assert result == expected_run_dir
        assert (result / HOUR_00).read_bytes() == first_path.read_bytes()
        assert (result / HOUR_01).read_bytes() == second_path.read_bytes()

        manifest = json.loads(
            (data_root / "bluesky" / DUMP_DATASET_ID / MANIFEST_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        expected_manifest_format = "parquet"
        expected_ingestion_config = DUMP_CONFIG_PATH.as_posix()
        assert manifest["format"] == expected_manifest_format
        assert manifest["ingestion_config"] == expected_ingestion_config
        assert manifest["dataset_id"] == DUMP_DATASET_ID

        metadata = json.loads((result / METADATA_FILENAME).read_text(encoding="utf-8"))
        expected_source_root = _expected_source_root(parquet_root)
        assert metadata["sync_status"] == "completed"
        assert metadata["dataset_id"] == DUMP_DATASET_ID
        assert metadata["sync_timestamp"] == DUMP_RAW_RUN_TIMESTAMP
        assert metadata["source"] == "jetstream_dump"
        assert metadata["row_count"] == EXPECTED_ROW_COUNT
        assert metadata["source_parquet_root"] == expected_source_root

    def test_raises_when_destination_run_exists(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Refuses to copy when the destination raw run directory already exists."""
        parquet_root = tmp_path / "parquet"
        _write_hive_parquet(parquet_root)
        run_dir = data_root / "bluesky" / DUMP_DATASET_ID / "raw" / DUMP_RAW_RUN_TIMESTAMP
        run_dir.mkdir(parents=True)
        leftover = run_dir / "leftover.txt"
        leftover.write_text("keep", encoding="utf-8")
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(FileExistsError):
            publish_dump_to_raw(
                parquet_root,
                DUMP_DATASET_ID,
                DUMP_RAW_RUN_TIMESTAMP,
                config_path,
            )

        expected = "keep"
        result = leftover.read_text(encoding="utf-8")
        assert result == expected
        assert not (run_dir / HOUR_00).exists()

    def test_raises_when_parquet_root_missing(self, data_root: Path, tmp_path: Path) -> None:
        """Raises FileNotFoundError when the dump parquet root does not exist."""
        parquet_root = tmp_path / "missing"
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(FileNotFoundError):
            publish_dump_to_raw(
                parquet_root,
                DUMP_DATASET_ID,
                DUMP_RAW_RUN_TIMESTAMP,
                config_path,
            )

    def test_raises_when_parquet_root_has_no_files(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Raises FileNotFoundError when the dump parquet root is empty."""
        parquet_root = tmp_path / "empty"
        parquet_root.mkdir()
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(FileNotFoundError):
            publish_dump_to_raw(
                parquet_root,
                DUMP_DATASET_ID,
                DUMP_RAW_RUN_TIMESTAMP,
                config_path,
            )


class TestJetstreamDumpYaml:
    """Tests for data_platform/preprocessing/configs/bluesky/jetstream_dump.yaml."""

    def test_committed_yaml_has_dump_dataset_and_sample_settings(self) -> None:
        """The dump YAML pins dataset id, parquet format, and sample settings."""
        loaded = yaml.safe_load(
            (REPO_ROOT / DUMP_CONFIG_PATH).read_text(encoding="utf-8")
        )

        result = {
            "dataset_id": loaded["dataset_id"],
            "output_format": loaded["output_format"],
            "raw_run_timestamp": loaded["dump"]["raw_run_timestamp"],
            "sample_size": loaded["preprocessing_params"]["sample_size"],
            "sample_seed": loaded["preprocessing_params"]["sample_seed"],
        }
        expected = {
            "dataset_id": DUMP_DATASET_ID,
            "output_format": "parquet",
            "raw_run_timestamp": DUMP_RAW_RUN_TIMESTAMP,
            "sample_size": EXPECTED_SAMPLE_SIZE,
            "sample_seed": EXPECTED_SAMPLE_SEED,
        }
        assert result == expected
