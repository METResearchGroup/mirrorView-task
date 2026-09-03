from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import yaml

from data_platform.preprocessing.preprocess_reddit import (
    load_dump_preprocess_settings,
    preprocess_records,
)
from data_platform.preprocessing.sample_records import (
    SOURCE_RAW_RUN_COLUMN,
    sample_records_per_source_run,
)
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import RedditStorageManager, StorageStage
from tests.data_platform.constants import VALID_REDDIT_DATASET_ID
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.preprocessing.test_preprocess_reddit import _valid_body

MAY_RUN = "2025_05_01-00:00:00"
JUNE_RUN = "2025_06_01-00:00:00"
SAMPLE_SEED = 20260903


def _keeper_row(comment_fullname: str) -> dict[str, Any]:
    row = mock_comment_row(comment_fullname)
    row["body"] = _valid_body()
    row["author"] = "regular_user"
    return row


def _frame_with_source_runs(may_count: int, june_count: int) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for index in range(may_count):
        row = _keeper_row(f"t1_may_{index}")
        row[SOURCE_RAW_RUN_COLUMN] = MAY_RUN
        rows.append(row)
    for index in range(june_count):
        row = _keeper_row(f"t1_june_{index}")
        row[SOURCE_RAW_RUN_COLUMN] = JUNE_RUN
        rows.append(row)
    return pd.DataFrame(rows)


class TestSampleRecordsPerSourceRun:
    """Tests for sample_records_per_source_run."""

    def test_samples_each_source_run_with_repeatable_seed(self) -> None:
        records = _frame_with_source_runs(5, 5)
        first = sample_records_per_source_run(
            records, 2, SAMPLE_SEED, SOURCE_RAW_RUN_COLUMN
        )
        second = sample_records_per_source_run(
            records, 2, SAMPLE_SEED, SOURCE_RAW_RUN_COLUMN
        )
        assert len(first) == 4
        assert (first[SOURCE_RAW_RUN_COLUMN] == MAY_RUN).sum() == 2
        assert (first[SOURCE_RAW_RUN_COLUMN] == JUNE_RUN).sum() == 2
        assert list(first["comment_fullname"]) == list(second["comment_fullname"])

    def test_keeps_short_group_in_order(self) -> None:
        records = _frame_with_source_runs(1, 1)
        result = sample_records_per_source_run(
            records, 2, SAMPLE_SEED, SOURCE_RAW_RUN_COLUMN
        )
        expected = ["t1_may_0", "t1_june_0"]
        assert list(result["comment_fullname"]) == expected

    def test_rejects_sample_size_below_one(self) -> None:
        records = _frame_with_source_runs(1, 1)
        with pytest.raises(ValueError, match="sample_size"):
            sample_records_per_source_run(
                records, 0, SAMPLE_SEED, SOURCE_RAW_RUN_COLUMN
            )

    def test_rejects_missing_source_column(self) -> None:
        records = pd.DataFrame([_keeper_row("t1_keep")])
        with pytest.raises(KeyError):
            sample_records_per_source_run(
                records, 1, SAMPLE_SEED, SOURCE_RAW_RUN_COLUMN
            )


class TestLoadDumpPreprocessSettings:
    """Tests for load_dump_preprocess_settings."""

    def test_reads_dataset_id_and_sample_settings(self, tmp_path: Path) -> None:
        config_path = tmp_path / "pushshift_dump.yaml"
        config_path.write_text(
            yaml.safe_dump(
                {
                    "dataset_id": VALID_REDDIT_DATASET_ID,
                    "preprocess": {
                        "sample_size": 200000,
                        "sample_seed": SAMPLE_SEED,
                    },
                }
            ),
            encoding="utf-8",
        )
        result = load_dump_preprocess_settings(config_path)
        expected = (VALID_REDDIT_DATASET_ID, 200000, SAMPLE_SEED)
        assert result == expected


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
    storage.write_run_metadata(run_dir, {"sync_status": "completed", "row_count": len(rows)})


class TestPreprocessRecordsSampling:
    """Tests that Reddit preprocess samples after filters when sample_size is set."""

    def test_config_path_samples_per_source_run(self, data_root: Path) -> None:
        dataset_id = VALID_REDDIT_DATASET_ID
        may_rows = [_keeper_row(f"t1_may_{index}") for index in range(5)]
        june_rows = [_keeper_row(f"t1_june_{index}") for index in range(5)]
        _write_parquet_raw_run(data_root, dataset_id, MAY_RUN, may_rows)
        _write_parquet_raw_run(data_root, dataset_id, JUNE_RUN, june_rows)

        output_dir = preprocess_records(
            dataset_id, sample_size=2, sample_seed=SAMPLE_SEED
        )

        storage = RedditStorageManager(StorageStage.PREPROCESSED, dataset_id)
        output = storage.load_records(output_dir)
        assert len(output) == 4
        assert SOURCE_RAW_RUN_COLUMN not in output.columns
        metadata = storage.load_run_metadata(output_dir)
        assert metadata["row_counts"]["output"] == 4

    def test_dataset_id_path_keeps_every_filtered_row(self, data_root: Path) -> None:
        dataset_id = VALID_REDDIT_DATASET_ID
        rows = [
            _keeper_row("t1_keep"),
            _keeper_row("t1_keep_two"),
        ]
        _write_parquet_raw_run(data_root, dataset_id, MAY_RUN, rows)

        output_dir = preprocess_records(dataset_id)

        storage = RedditStorageManager(StorageStage.PREPROCESSED, dataset_id)
        output = storage.load_records(output_dir)
        assert len(output) == 2
        assert SOURCE_RAW_RUN_COLUMN not in output.columns
