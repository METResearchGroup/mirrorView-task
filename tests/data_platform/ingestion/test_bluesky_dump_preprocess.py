from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from data_platform.ingestion.data_dumps.bluesky.load_raw import load_hive_dump_posts
from data_platform.ingestion.data_dumps.bluesky.publish_dump_to_raw import (
    DUMP_CONFIG_PATH,
    DUMP_DATASET_ID,
    DUMP_RAW_RUN_TIMESTAMP,
    publish_dump_to_raw,
)
from data_platform.ingestion.data_dumps.bluesky.transform import dump_post_to_sync_row
from data_platform.ingestion.generate_record_id import (
    INTEGRATION_BLUESKY,
    attach_record_id,
)
from data_platform.models.sync import SyncBlueskyPostModel
from data_platform.preprocessing.preprocess_bluesky import (
    BLUESKY_SPEC,
    preprocess_records,
)
from data_platform.preprocessing.runner import preprocess_records as run_preprocess_records
from data_platform.preprocessing.sample import sample_rows
from data_platform.utils.dataset import MANIFEST_FILENAME, ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import (
    METADATA_FILENAME,
    BlueskyStorageManager,
    StorageStage,
)
from lib.constants import REPO_ROOT
from tests.data_platform.constants import VALID_DATASET_ID

VALID_BLUESKY_POST_TEXT = (
    "This is a valid English bluesky post for preprocessing tests without any "
    "links and with enough words that length and language checks both pass here."
)

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


DUMP_DID = "did:plc:abc"
DUMP_URI = f"at://{DUMP_DID}/app.bsky.feed.post/rkey1"
DUMP_CREATED_AT = "2026-09-01T00:00:00+00:00"
HIVE_RUN_TIMESTAMP = "2026_09_01-00:00:00"
SAMPLE_SEED = 20260901


def _dump_row(
    uri: str = DUMP_URI,
    did: str = DUMP_DID,
    text: str = "hello",
    created_at: str = DUMP_CREATED_AT,
) -> dict[str, object]:
    return {
        "uri": uri,
        "did": did,
        "created_at": created_at,
        "text": text,
    }


def _write_dump_parquet(path: Path, rows: list[dict[str, object]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_parquet(path, index=False)
    return path


def _write_hive_raw_run(
    data_root: Path,
    dataset_id: str,
    rows_by_hour: dict[str, list[dict[str, object]]],
) -> Path:
    write_dataset_manifest(
        "bluesky",
        dataset_id,
        name="dump-test",
        ingestion_config=DUMP_CONFIG_PATH.as_posix(),
        data_format=ValidDataFormats.PARQUET,
    )
    run_dir = data_root / "bluesky" / dataset_id / "raw" / HIVE_RUN_TIMESTAMP
    for hour, rows in rows_by_hour.items():
        _write_dump_parquet(
            run_dir / "date=2026-09-01" / f"hour={hour}" / f"{hour}.parquet",
            rows,
        )
    (run_dir / METADATA_FILENAME).write_text(
        json.dumps({"sync_status": "completed"}),
        encoding="utf-8",
    )
    return run_dir


class TestDumpPostToSyncRow:
    """Tests for dump_post_to_sync_row()."""

    def test_maps_dump_row_onto_bluesky_ingest_model(self) -> None:
        """Mapped dump posts validate as ingest rows and use the DID as handle."""
        row = _dump_row()

        result = dump_post_to_sync_row(row, HIVE_RUN_TIMESTAMP)
        expected_record_id = attach_record_id({"uri": DUMP_URI}, INTEGRATION_BLUESKY)[
            "record_id"
        ]
        expected_url = f"https://bsky.app/profile/{DUMP_DID}/post/rkey1"

        SyncBlueskyPostModel.model_validate(result)
        assert result["author_handle"] == DUMP_DID
        assert result["url"] == expected_url
        assert result["record_id"] == expected_record_id
        assert result["like_count"] == 0
        assert result["repost_count"] == 0
        assert result["reply_count"] == 0
        assert result["quote_count"] == 0
        assert result["sync_timestamp"] == HIVE_RUN_TIMESTAMP
        assert "did" not in result

    def test_maps_datetime_created_at_to_isoformat(self) -> None:
        """Datetime created_at values become UTC ISO-8601 strings."""
        row = _dump_row()
        row["created_at"] = datetime(2026, 9, 1, tzinfo=timezone.utc)

        result = dump_post_to_sync_row(row, HIVE_RUN_TIMESTAMP)

        expected = "2026-09-01T00:00:00+00:00"
        assert result["created_at"] == expected

    def test_raises_when_uri_missing(self) -> None:
        """Raises KeyError when uri is missing from the dump row."""
        row = _dump_row()
        del row["uri"]

        with pytest.raises(KeyError):
            dump_post_to_sync_row(row, HIVE_RUN_TIMESTAMP)

    def test_raises_when_uri_has_no_slash(self) -> None:
        """Raises ValueError when uri has no slash to split an rkey from."""
        row = _dump_row(uri="not-an-at-uri")

        with pytest.raises(ValueError):
            dump_post_to_sync_row(row, HIVE_RUN_TIMESTAMP)


class TestLoadHiveDumpPosts:
    """Tests for load_hive_dump_posts()."""

    def test_loads_parquet_files_in_sorted_path_order(self, tmp_path: Path) -> None:
        """Rows from later hour paths follow earlier hour paths."""
        run_dir = tmp_path / HIVE_RUN_TIMESTAMP
        first = _dump_row(uri=f"at://{DUMP_DID}/app.bsky.feed.post/aaa", text="first")
        second = _dump_row(uri=f"at://{DUMP_DID}/app.bsky.feed.post/bbb", text="second")
        _write_dump_parquet(
            run_dir / "date=2026-09-01" / "hour=00" / "a.parquet",
            [first],
        )
        _write_dump_parquet(
            run_dir / "date=2026-09-01" / "hour=01" / "b.parquet",
            [second],
        )

        result = load_hive_dump_posts(run_dir, HIVE_RUN_TIMESTAMP)

        expected = ["first", "second"]
        texts = [row["text"] for row in result]
        assert texts == expected
        for row in result:
            SyncBlueskyPostModel.model_validate(row)

    def test_drops_blank_text_rows(self, tmp_path: Path) -> None:
        """Blank dump text is skipped and valid rows remain."""
        run_dir = tmp_path / HIVE_RUN_TIMESTAMP
        kept = _dump_row(text="kept")
        blank = _dump_row(
            uri=f"at://{DUMP_DID}/app.bsky.feed.post/blank",
            text="   ",
        )
        _write_dump_parquet(
            run_dir / "date=2026-09-01" / "hour=00" / "a.parquet",
            [kept, blank],
        )

        result = load_hive_dump_posts(run_dir, HIVE_RUN_TIMESTAMP)

        expected = ["kept"]
        texts = [row["text"] for row in result]
        assert texts == expected

    def test_raises_when_run_dir_has_no_parquet(self, tmp_path: Path) -> None:
        """Raises FileNotFoundError when the raw run has no parquet files."""
        run_dir = tmp_path / HIVE_RUN_TIMESTAMP
        run_dir.mkdir()

        with pytest.raises(FileNotFoundError):
            load_hive_dump_posts(run_dir, HIVE_RUN_TIMESTAMP)


class TestSampleRows:
    """Tests for sample_rows()."""

    def test_samples_repeatably_with_the_same_seed(self) -> None:
        """The same seed returns the same uri set."""
        records = pd.DataFrame({"uri": [f"u{index}" for index in range(5)]})

        first = sample_rows(records, 3, SAMPLE_SEED)
        second = sample_rows(records, 3, SAMPLE_SEED)

        expected = 3
        assert len(first) == expected
        assert set(first["uri"]) == set(second["uri"])

    def test_returns_all_rows_when_shorter_than_sample_size(self) -> None:
        """A frame shorter than sample_size is returned in full."""
        records = pd.DataFrame({"uri": ["a", "b"]})

        result = sample_rows(records, 5, SAMPLE_SEED)

        expected = ["a", "b"]
        assert list(result["uri"]) == expected

    def test_raises_when_sample_size_is_below_one(self) -> None:
        """Raises ValueError when sample_size is less than 1."""
        records = pd.DataFrame({"uri": ["a"]})

        with pytest.raises(ValueError, match="sample_size"):
            sample_rows(records, 0, SAMPLE_SEED)


class TestPreprocessRecordsSampling:
    """Tests for preprocess_records() dump hive load and sampling."""

    def test_samples_kept_hive_rows_before_write(self, data_root: Path) -> None:
        """Hive dump raw runs map, filter, sample, and record sample metadata."""
        rows = [
            _dump_row(
                uri=f"at://{DUMP_DID}/app.bsky.feed.post/p{index}",
                text=f"{VALID_BLUESKY_POST_TEXT} {index}",
            )
            for index in range(3)
        ]
        _write_hive_raw_run(data_root, VALID_DATASET_ID, {"00": rows})

        output_dir = run_preprocess_records(
            VALID_DATASET_ID,
            BLUESKY_SPEC,
            2,
            SAMPLE_SEED,
        )
        output = BlueskyStorageManager(
            StorageStage.PREPROCESSED, VALID_DATASET_ID
        ).load_records(output_dir)
        metadata = json.loads((output_dir / METADATA_FILENAME).read_text(encoding="utf-8"))

        expected = 2
        assert len(output) == expected
        assert metadata["row_counts"]["sampled"] == expected
        assert metadata["sample_size"] == expected
        assert metadata["sample_seed"] == SAMPLE_SEED
        assert "did" not in output.columns

    def test_writes_every_kept_row_when_sample_size_is_none(
        self, data_root: Path
    ) -> None:
        """Keyword-style preprocess still writes every kept hive row."""
        rows = [
            _dump_row(
                uri=f"at://{DUMP_DID}/app.bsky.feed.post/p{index}",
                text=f"{VALID_BLUESKY_POST_TEXT} {index}",
            )
            for index in range(3)
        ]
        _write_hive_raw_run(data_root, VALID_DATASET_ID, {"00": rows})

        output_dir = preprocess_records(VALID_DATASET_ID)
        output = BlueskyStorageManager(
            StorageStage.PREPROCESSED, VALID_DATASET_ID
        ).load_records(output_dir)
        metadata = json.loads((output_dir / METADATA_FILENAME).read_text(encoding="utf-8"))

        expected = 3
        assert len(output) == expected
        assert "sample_size" not in metadata
        assert "sampled" not in metadata["row_counts"]
