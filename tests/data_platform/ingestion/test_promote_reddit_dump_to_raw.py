from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from data_platform.ingestion.data_dumps.reddit.promote_to_raw import (
    COMMENTS_PARQUET_FILENAME,
    DUMP_DATASET_CONFIG,
    promote_dump_sources_to_raw,
)
from data_platform.utils.storage import RedditStorageManager, StorageStage
from tests.data_platform.constants import VALID_REDDIT_DATASET_ID

MAY_RUN = "2025_05_01-00:00:00"
JUNE_RUN = "2025_06_01-00:00:00"
MAY_POINTER = "may-lfs-pointer"
JUNE_POINTER = "june-lfs-pointer"
EXISTING_POINTER = "do-not-overwrite"


def _write_dump_config(
    tmp_path: Path,
    *,
    may_source: Path,
    june_source: Path,
    dataset_id: str = VALID_REDDIT_DATASET_ID,
) -> Path:
    config_path = tmp_path / "pushshift_dump.yaml"
    payload = {
        "dataset_id": dataset_id,
        "name": "reddit-pushshift-dump-test",
        "description": "Test dump promote",
        "output_format": "parquet",
        "record_types": ["reddit.comment"],
        "sources": [
            {"parquet": str(may_source), "raw_run": MAY_RUN},
            {"parquet": str(june_source), "raw_run": JUNE_RUN},
        ],
        "preprocess": {"sample_size": 200000, "sample_seed": 20260903},
    }
    config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")
    return config_path


def _write_source_pair(tmp_path: Path) -> tuple[Path, Path]:
    may_source = tmp_path / "RC_2025-05.parquet"
    june_source = tmp_path / "RC_2025-06.parquet"
    may_source.write_text(MAY_POINTER, encoding="utf-8")
    june_source.write_text(JUNE_POINTER, encoding="utf-8")
    return may_source, june_source


class TestPromoteDumpSourcesToRaw:
    """Tests for promote_dump_sources_to_raw."""

    def test_copies_sources_into_named_raw_runs(self, data_root: Path, tmp_path: Path) -> None:
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = _write_dump_config(
            tmp_path, may_source=may_source, june_source=june_source
        )

        result = promote_dump_sources_to_raw(config_path, data_root)

        expected_root = data_root / "reddit" / VALID_REDDIT_DATASET_ID
        assert result == expected_root
        may_dest = expected_root / "raw" / MAY_RUN / COMMENTS_PARQUET_FILENAME
        june_dest = expected_root / "raw" / JUNE_RUN / COMMENTS_PARQUET_FILENAME
        assert may_dest.read_text(encoding="utf-8") == MAY_POINTER
        assert june_dest.read_text(encoding="utf-8") == JUNE_POINTER
        manifest = json.loads((expected_root / "dataset.json").read_text(encoding="utf-8"))
        assert manifest["format"] == "parquet"
        assert manifest["ingestion_config"].endswith("pushshift_dump.yaml")
        may_meta = json.loads(
            (expected_root / "raw" / MAY_RUN / "metadata.json").read_text(encoding="utf-8")
        )
        june_meta = json.loads(
            (expected_root / "raw" / JUNE_RUN / "metadata.json").read_text(encoding="utf-8")
        )
        assert may_meta["sync_status"] == "completed"
        assert june_meta["sync_status"] == "completed"
        assert may_meta["source_dump_file"].endswith("RC_2025-05.parquet")
        assert june_meta["source_dump_file"].endswith("RC_2025-06.parquet")

    def test_missing_source_writes_no_destination(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        may_source = tmp_path / "RC_2025-05.parquet"
        june_source = tmp_path / "missing.parquet"
        may_source.write_text(MAY_POINTER, encoding="utf-8")
        config_path = _write_dump_config(
            tmp_path, may_source=may_source, june_source=june_source
        )

        with pytest.raises(FileNotFoundError):
            promote_dump_sources_to_raw(config_path, data_root)

        dest_root = data_root / "reddit" / VALID_REDDIT_DATASET_ID / "raw"
        assert not (dest_root / MAY_RUN / COMMENTS_PARQUET_FILENAME).exists()
        assert not (dest_root / JUNE_RUN / COMMENTS_PARQUET_FILENAME).exists()

    def test_existing_destination_is_not_overwritten(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = _write_dump_config(
            tmp_path, may_source=may_source, june_source=june_source
        )
        dest = (
            data_root
            / "reddit"
            / VALID_REDDIT_DATASET_ID
            / "raw"
            / MAY_RUN
            / COMMENTS_PARQUET_FILENAME
        )
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_text(EXISTING_POINTER, encoding="utf-8")

        with pytest.raises(FileExistsError):
            promote_dump_sources_to_raw(config_path, data_root)

        assert dest.read_text(encoding="utf-8") == EXISTING_POINTER

    def test_storage_manager_uses_comments_parquet(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = _write_dump_config(
            tmp_path, may_source=may_source, june_source=june_source
        )

        promote_dump_sources_to_raw(config_path, data_root)

        storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
        assert storage.records_filename == COMMENTS_PARQUET_FILENAME

    def test_rejects_csv_output_format(self, data_root: Path, tmp_path: Path) -> None:
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = _write_dump_config(
            tmp_path, may_source=may_source, june_source=june_source
        )
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8"))
        payload["output_format"] = "csv"
        config_path.write_text(yaml.safe_dump(payload), encoding="utf-8")

        with pytest.raises(ValueError, match="parquet"):
            promote_dump_sources_to_raw(config_path, data_root)


def test_committed_dump_yaml_pins_dataset_and_sources() -> None:
    payload = yaml.safe_load(DUMP_DATASET_CONFIG.read_text(encoding="utf-8"))
    assert payload["dataset_id"] == "reddit_3d8a2c41-9b17-4e6f-a5d0-8c1b2e4f6079"
    assert payload["output_format"] == "parquet"
    assert payload["preprocess"]["sample_size"] == 200000
    sources = payload["sources"]
    assert sources[0]["raw_run"] == MAY_RUN
    assert sources[1]["raw_run"] == JUNE_RUN
