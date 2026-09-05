from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import typer
import yaml

from data_platform.ingestion.data_dumps.reddit.publish_dump_to_raw import (
    COMMENTS_PARQUET_FILENAME,
    DUMP_CONFIG_PATH,
    DUMP_DATASET_ID,
    DUMP_DATASET_NAME,
    DUMP_SOURCE,
    DUMP_SOURCES,
    publish_dump_to_raw,
)
from data_platform.preprocessing.preprocess_reddit import (
    REDDIT_SPEC,
    _resolve_preprocess_cli,
    _sample_size_from_yaml,
    preprocess_records,
)
from data_platform.preprocessing.runner import preprocess_records as run_preprocess_records
from data_platform.utils.dataset import MANIFEST_FILENAME, ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import (
    METADATA_FILENAME,
    RedditStorageManager,
    StorageStage,
)
from lib.constants import REPO_ROOT
from tests.data_platform.constants import VALID_REDDIT_DATASET_ID
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.preprocessing.test_preprocess_reddit import _valid_body

MAY_RUN = "2025_05_01-00:00:00"
JUNE_RUN = "2025_06_01-00:00:00"
MAY_POINTER = "may-lfs-pointer"
JUNE_POINTER = "june-lfs-pointer"
EXISTING_POINTER = "do-not-overwrite"
EXPECTED_SAMPLE_SIZE = 400000


def _keeper_row(comment_fullname: str) -> dict[str, Any]:
    row = mock_comment_row(comment_fullname)
    row["body"] = _valid_body()
    row["author"] = "regular_user"
    return row


def _write_source_pair(tmp_path: Path) -> tuple[Path, Path]:
    may_source = tmp_path / "RC_2025-05.parquet"
    june_source = tmp_path / "RC_2025-06.parquet"
    may_source.write_text(MAY_POINTER, encoding="utf-8")
    june_source.write_text(JUNE_POINTER, encoding="utf-8")
    return may_source, june_source


def _write_parquet_raw_run(
    data_root: Path,
    dataset_id: str,
    run_name: str,
    rows: list[dict[str, Any]],
) -> None:
    write_dataset_manifest(
        "reddit",
        dataset_id,
        name="dump-test",
        ingestion_config="test.yaml",
        data_format=ValidDataFormats.PARQUET,
    )
    storage = RedditStorageManager(StorageStage.RAW, dataset_id)
    run_dir = data_root / "reddit" / dataset_id / "raw" / run_name
    run_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(run_dir / storage.records_filename, index=False)
    storage.write_run_metadata(
        run_dir, {"sync_status": "completed", "row_count": len(rows)}
    )


class TestPublishDumpToRaw:
    """Tests for publish_dump_to_raw()."""

    def test_copies_sources_into_named_raw_runs(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Copies parquet bytes and writes dataset.json plus completed metadata."""
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        result = publish_dump_to_raw(
            [(may_source, MAY_RUN), (june_source, JUNE_RUN)],
            DUMP_DATASET_ID,
            config_path,
        )

        expected_root = data_root / "reddit" / DUMP_DATASET_ID
        may_dest = expected_root / "raw" / MAY_RUN / COMMENTS_PARQUET_FILENAME
        june_dest = expected_root / "raw" / JUNE_RUN / COMMENTS_PARQUET_FILENAME
        assert result == [
            expected_root / "raw" / MAY_RUN,
            expected_root / "raw" / JUNE_RUN,
        ]
        assert may_dest.read_text(encoding="utf-8") == MAY_POINTER
        assert june_dest.read_text(encoding="utf-8") == JUNE_POINTER

        manifest = json.loads(
            (expected_root / MANIFEST_FILENAME).read_text(encoding="utf-8")
        )
        assert manifest["format"] == "parquet"
        assert manifest["ingestion_config"] == DUMP_CONFIG_PATH.as_posix()
        assert manifest["dataset_id"] == DUMP_DATASET_ID
        assert manifest["name"] == DUMP_DATASET_NAME

        may_meta = json.loads(
            (expected_root / "raw" / MAY_RUN / METADATA_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        june_meta = json.loads(
            (expected_root / "raw" / JUNE_RUN / METADATA_FILENAME).read_text(
                encoding="utf-8"
            )
        )
        assert may_meta["sync_status"] == "completed"
        assert june_meta["sync_status"] == "completed"
        assert may_meta["source"] == DUMP_SOURCE
        assert june_meta["source"] == DUMP_SOURCE
        assert may_meta["sync_timestamp"] == MAY_RUN
        assert june_meta["sync_timestamp"] == JUNE_RUN
        assert may_meta["source_dump_file"] == may_source.resolve().as_posix()
        assert june_meta["source_dump_file"] == june_source.resolve().as_posix()

    def test_raises_when_destination_run_exists(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Refuses to copy when a destination raw run directory already exists."""
        may_source, june_source = _write_source_pair(tmp_path)
        run_dir = data_root / "reddit" / DUMP_DATASET_ID / "raw" / MAY_RUN
        run_dir.mkdir(parents=True)
        leftover = run_dir / "leftover.txt"
        leftover.write_text(EXISTING_POINTER, encoding="utf-8")
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(FileExistsError):
            publish_dump_to_raw(
                [(may_source, MAY_RUN), (june_source, JUNE_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

        assert leftover.read_text(encoding="utf-8") == EXISTING_POINTER
        assert not (run_dir / COMMENTS_PARQUET_FILENAME).exists()
        assert not (
            data_root / "reddit" / DUMP_DATASET_ID / "raw" / JUNE_RUN
        ).exists()

    def test_missing_source_writes_no_destination(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Raises FileNotFoundError when a source parquet file is missing."""
        may_source = tmp_path / "RC_2025-05.parquet"
        june_source = tmp_path / "missing.parquet"
        may_source.write_text(MAY_POINTER, encoding="utf-8")
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(FileNotFoundError):
            publish_dump_to_raw(
                [(may_source, MAY_RUN), (june_source, JUNE_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

        dest_root = data_root / "reddit" / DUMP_DATASET_ID / "raw"
        assert not (dest_root / MAY_RUN / COMMENTS_PARQUET_FILENAME).exists()
        assert not (dest_root / JUNE_RUN / COMMENTS_PARQUET_FILENAME).exists()

    def test_rejects_non_parquet_source(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Rejects a source path that does not use the parquet suffix."""
        may_source = tmp_path / "RC_2025-05.csv"
        june_source = tmp_path / "RC_2025-06.parquet"
        may_source.write_text(MAY_POINTER, encoding="utf-8")
        june_source.write_text(JUNE_POINTER, encoding="utf-8")
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(ValueError, match="parquet"):
            publish_dump_to_raw(
                [(may_source, MAY_RUN), (june_source, JUNE_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

    def test_rejects_unsafe_raw_run_name(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Rejects a raw_run value that can escape the dataset raw directory."""
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(ValueError, match="directory name"):
            publish_dump_to_raw(
                [(may_source, "../escape"), (june_source, JUNE_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

    def test_rejects_duplicate_raw_run_names(
        self, data_root: Path, tmp_path: Path
    ) -> None:
        """Rejects two sources that share a raw_run folder name."""
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = REPO_ROOT / DUMP_CONFIG_PATH

        with pytest.raises(ValueError, match="unique"):
            publish_dump_to_raw(
                [(may_source, MAY_RUN), (june_source, MAY_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

    def test_removes_incomplete_runs_when_copy_fails(
        self, data_root: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Deletes every new raw run directory when publication fails after mkdir."""
        may_source, june_source = _write_source_pair(tmp_path)
        config_path = REPO_ROOT / DUMP_CONFIG_PATH
        dest_root = data_root / "reddit" / DUMP_DATASET_ID / "raw"

        def _fail_copy(*_args: object, **_kwargs: object) -> None:
            raise OSError("copy failed")

        monkeypatch.setattr(
            "data_platform.ingestion.data_dumps.reddit.publish_dump_to_raw._copy_source_to_raw_run",
            _fail_copy,
        )

        with pytest.raises(OSError, match="copy failed"):
            publish_dump_to_raw(
                [(may_source, MAY_RUN), (june_source, JUNE_RUN)],
                DUMP_DATASET_ID,
                config_path,
            )

        assert not (dest_root / MAY_RUN).exists()
        assert not (dest_root / JUNE_RUN).exists()


class TestCommittedDumpYaml:
    """Tests for data_platform/preprocessing/configs/reddit/pushshift_dump.yaml."""

    def test_committed_yaml_has_dump_dataset_and_sample_settings(self) -> None:
        """The dump YAML pins dataset id, parquet format, and sample settings."""
        loaded = yaml.safe_load(
            (REPO_ROOT / DUMP_CONFIG_PATH).read_text(encoding="utf-8")
        )
        yaml_sources = [
            (Path(source["parquet"]), source["raw_run"])
            for source in loaded["dump"]["sources"]
        ]

        result = {
            "dataset_id": loaded["dataset_id"],
            "output_format": loaded["output_format"],
            "sources": yaml_sources,
            "sample_size": loaded["preprocessing_params"]["sample_size"],
        }
        expected = {
            "dataset_id": DUMP_DATASET_ID,
            "output_format": "parquet",
            "sources": list(DUMP_SOURCES),
            "sample_size": EXPECTED_SAMPLE_SIZE,
        }
        assert result == expected
        assert "sample_seed" not in loaded["preprocessing_params"]


class TestPreprocessRecordsSampling:
    """Tests for Reddit preprocess sampling after filters."""

    def test_samples_kept_rows_before_write(self, data_root: Path) -> None:
        """Dump raw runs filter, sample, and record sample metadata."""
        may_rows = [_keeper_row(f"t1_may_{index}") for index in range(5)]
        june_rows = [_keeper_row(f"t1_june_{index}") for index in range(5)]
        _write_parquet_raw_run(data_root, VALID_REDDIT_DATASET_ID, MAY_RUN, may_rows)
        _write_parquet_raw_run(data_root, VALID_REDDIT_DATASET_ID, JUNE_RUN, june_rows)

        output_dir = run_preprocess_records(
            VALID_REDDIT_DATASET_ID,
            REDDIT_SPEC,
            4,
        )
        storage = RedditStorageManager(
            StorageStage.PREPROCESSED, VALID_REDDIT_DATASET_ID
        )
        output = storage.load_records(output_dir)
        metadata = json.loads((output_dir / METADATA_FILENAME).read_text(encoding="utf-8"))

        expected = 4
        assert len(output) == expected
        assert metadata["row_counts"]["sampled"] == expected
        assert metadata["sample_size"] == expected
        assert "sample_seed" not in metadata
        assert "source_raw_run" not in output.columns

    def test_writes_every_kept_row_when_sample_size_is_none(
        self, data_root: Path
    ) -> None:
        """`--dataset-id` preprocess still writes every kept row."""
        rows = [_keeper_row("t1_keep"), _keeper_row("t1_keep_two")]
        _write_parquet_raw_run(data_root, VALID_REDDIT_DATASET_ID, MAY_RUN, rows)

        output_dir = preprocess_records(VALID_REDDIT_DATASET_ID)
        storage = RedditStorageManager(
            StorageStage.PREPROCESSED, VALID_REDDIT_DATASET_ID
        )
        output = storage.load_records(output_dir)
        metadata = json.loads((output_dir / METADATA_FILENAME).read_text(encoding="utf-8"))

        expected = 2
        assert len(output) == expected
        assert "sample_size" not in metadata
        assert "sampled" not in metadata["row_counts"]


class TestSampleSizeFromYaml:
    """Tests for _sample_size_from_yaml()."""

    def test_reads_sample_size_from_preprocessing_params(self) -> None:
        """Returns the integer sample_size from preprocessing_params."""
        result = _sample_size_from_yaml(
            {"preprocessing_params": {"sample_size": EXPECTED_SAMPLE_SIZE}}
        )

        expected = EXPECTED_SAMPLE_SIZE
        assert result == expected

    def test_raises_when_sample_size_is_missing(self) -> None:
        """Rejects a config that omits preprocessing_params.sample_size."""
        with pytest.raises(typer.BadParameter, match="sample_size"):
            _sample_size_from_yaml({"preprocessing_params": {}})

    @pytest.mark.parametrize("sample_size", ["abc", 1.9, True, 0, -1])
    def test_raises_when_sample_size_is_not_a_positive_integer(
        self, sample_size: object
    ) -> None:
        """Rejects malformed, fractional, boolean, and non-positive sample sizes."""
        with pytest.raises(typer.BadParameter, match="positive integer"):
            _sample_size_from_yaml({"preprocessing_params": {"sample_size": sample_size}})


class TestResolvePreprocessCli:
    """Tests for _resolve_preprocess_cli()."""

    @pytest.mark.parametrize("sample_size", [0, -1, True])
    def test_rejects_invalid_sample_size_with_dataset_id(
        self, sample_size: object
    ) -> None:
        """`--dataset-id` still rejects a non-positive sample-size override."""
        with pytest.raises(typer.BadParameter, match="positive integer"):
            _resolve_preprocess_cli(
                VALID_REDDIT_DATASET_ID,
                None,
                sample_size,  # type: ignore[arg-type]
            )
