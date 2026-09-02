from __future__ import annotations

import json

import pytest

from data_platform.constants import COMMENTS_FILENAME, POSTS_FILENAME
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.paths import resolve_package_path
from data_platform.utils.storage import BlueskyStorageManager, RedditStorageManager, StorageStage
from tests.data_platform.conftest import make_ingestion_row
from tests.data_platform.constants import VALID_DATASET_ID, VALID_REDDIT_DATASET_ID
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row


def _records_path(run_dir: str, file_name: str = POSTS_FILENAME) -> str:
    return f"{run_dir}/{file_name}"


class TestCreateNewRunDir:
    """Tests for StorageManager.create_new_run_dir."""

    def test_returns_package_relative_directory(self, data_root, bluesky_storage) -> None:
        result = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        expected = f"data/bluesky/{VALID_DATASET_ID}/raw/2026_05_30-10:00:00"
        assert result == expected
        assert resolve_package_path(result).is_dir()


class TestLatestRunDir:
    """Tests for StorageManager.latest_run_dir."""

    def test_latest_run_dir_scoped_to_dataset(self, data_root, bluesky_storage) -> None:
        other_id = "bluesky_00000000-0000-4000-8000-000000000002"
        storage_b = BlueskyStorageManager(StorageStage.RAW, other_id)

        run_a = bluesky_storage.create_new_run_dir("2026_05_29-10:00:00")
        storage_b.create_new_run_dir("2026_05_29-11:00:00")

        assert bluesky_storage.latest_run_dir() == run_a


class TestBlueskyStorageRoot:
    """Tests for StorageManager.root_dir."""

    def test_bluesky_storage_root_includes_dataset_id(self, data_root, bluesky_storage) -> None:
        assert bluesky_storage.root_dir == data_root / "bluesky" / VALID_DATASET_ID / "raw"


class TestWriteAndLoadRecords:
    """Tests for StorageManager.write_records and load_records."""

    def test_csv_round_trip(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(run_dir)
        row = make_ingestion_row()

        result = bluesky_storage.write_records([row], relative_file_path)
        loaded = bluesky_storage.load_records(relative_file_path)

        assert result == relative_file_path
        assert len(loaded) == 1
        assert loaded.iloc[0]["uri"] == row["uri"]

    def test_parquet_round_trip(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = f"{run_dir}/posts.parquet"
        row = make_ingestion_row()

        bluesky_storage.write_records([row], relative_file_path)
        loaded = bluesky_storage.load_records(relative_file_path)

        assert len(loaded) == 1
        assert loaded.iloc[0]["uri"] == row["uri"]
        assert resolve_package_path(relative_file_path).suffix == ".parquet"

    def test_unsupported_suffix_raises(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        with pytest.raises(ValueError, match="Unsupported records file suffix"):
            bluesky_storage.write_records([make_ingestion_row()], f"{run_dir}/posts.json")

    def test_write_records_validates_rows(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-11:00:00")
        with pytest.raises(Exception):
            bluesky_storage.write_records(
                [{"uri": "at://missing-fields"}],
                _records_path(run_dir),
            )

    def test_constructor_rejects_records_filename(self) -> None:
        with pytest.raises(TypeError):
            BlueskyStorageManager(
                StorageStage.RAW,
                VALID_DATASET_ID,
                records_filename="posts.csv",
            )


class TestAppendRecords:
    """Tests for StorageManager.append_records."""

    def test_append_records_writes_header_once(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(run_dir)

        bluesky_storage.append_records([make_ingestion_row()], relative_file_path)
        second_row = make_ingestion_row(uri="at://did:plc:example/app.bsky.feed.post/def")
        bluesky_storage.append_records([second_row], relative_file_path)

        csv_path = resolve_package_path(relative_file_path)
        lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
        assert lines[0].startswith("uri,")
        assert len(lines) == 3


class TestLoadSeenUris:
    """Tests for StorageManager.load_seen_uris."""

    def test_load_seen_uris(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(run_dir)
        row = make_ingestion_row()
        bluesky_storage.append_records([row], relative_file_path)

        assert bluesky_storage.load_seen_uris(relative_file_path) == {row["uri"]}


class TestAppendDedupedRecords:
    """Tests for StorageManager.append_deduped_records."""

    def test_append_deduped_records_skips_current_run_duplicates(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(run_dir)
        existing = [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")]
        bluesky_storage.append_records(existing, relative_file_path)
        config = DedupeConfig(id_column="uri")
        dedupe_session = DedupeSession(config)
        dedupe_session.warm(bluesky_storage, relative_file_path)

        result = bluesky_storage.append_deduped_records(
            [
                make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1"),
                make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a2"),
            ],
            relative_file_path,
            dedupe_session=dedupe_session,
        )

        assert result.kept == 1
        assert result.skipped == 1
        assert bluesky_storage.load_seen_uris(relative_file_path) == {
            "at://did:plc:ex/app.bsky.feed.post/a1",
            "at://did:plc:ex/app.bsky.feed.post/a2",
        }

    def test_append_deduped_records_skips_prior_run_duplicates(self, data_root) -> None:
        comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
        current_run = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(current_run, COMMENTS_FILENAME)
        comment_storage.append_records(
            [mock_comment_row("t1_comment_a")],
            relative_file_path,
        )
        config = DedupeConfig(id_column="comment_fullname", filename=COMMENTS_FILENAME)
        dedupe_session = DedupeSession(config)
        dedupe_session.warm(comment_storage, relative_file_path)

        result = comment_storage.append_deduped_records(
            [
                mock_comment_row("t1_comment_a"),
                mock_comment_row("t1_comment_b"),
            ],
            relative_file_path,
            dedupe_session=dedupe_session,
        )

        assert result.kept == 1
        assert result.skipped == 1
        assert comment_storage.load_seen_ids_from_disk(
            relative_file_path, "comment_fullname"
        ) == {"t1_comment_a", "t1_comment_b"}

    def test_append_deduped_records_skips_ids_from_prior_run_dirs(self, bluesky_storage) -> None:
        prior_run = bluesky_storage.create_new_run_dir("2026_05_29-10:00:00")
        current_run = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        prior_uri = "at://did:plc:ex/app.bsky.feed.post/prior"
        bluesky_storage.append_records(
            [make_ingestion_row(uri=prior_uri)], _records_path(prior_run)
        )
        current_path = _records_path(current_run)
        config = DedupeConfig(id_column="uri", include_prior_runs=True)
        dedupe_session = DedupeSession(config)
        dedupe_session.warm(bluesky_storage, current_path)

        result = bluesky_storage.append_deduped_records(
            [
                make_ingestion_row(uri=prior_uri),
                make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/new"),
            ],
            current_path,
            dedupe_session=dedupe_session,
        )

        assert result.kept == 1
        assert result.skipped == 1
        assert bluesky_storage.load_seen_ids_from_all_runs("uri", POSTS_FILENAME) == {
            prior_uri,
            "at://did:plc:ex/app.bsky.feed.post/new",
        }

    def test_append_deduped_records_does_not_dedupe_across_datasets(self, data_root) -> None:
        dataset_a = "reddit_00000000-0000-4000-8000-000000000001"
        dataset_b = "reddit_00000000-0000-4000-8000-000000000002"
        storage_a = RedditStorageManager(StorageStage.RAW, dataset_a)
        storage_b = RedditStorageManager(StorageStage.RAW, dataset_b)
        prior_run_a = storage_a.create_new_run_dir("2026_05_29-10:00:00")
        current_run_b = storage_b.create_new_run_dir("2026_05_30-10:00:00")
        storage_a.append_records(
            [mock_comment_row("t1_comment_a")],
            _records_path(prior_run_a, COMMENTS_FILENAME),
        )
        current_path = _records_path(current_run_b, COMMENTS_FILENAME)
        config = DedupeConfig(id_column="comment_fullname", filename=COMMENTS_FILENAME)
        dedupe_session = DedupeSession(config)
        dedupe_session.warm(storage_b, current_path)

        result = storage_b.append_deduped_records(
            [
                mock_comment_row("t1_comment_a"),
                mock_comment_row("t1_comment_b"),
            ],
            current_path,
            dedupe_session=dedupe_session,
        )

        assert result.kept == 2
        assert result.skipped == 0

    def test_append_deduped_records_returns_empty_when_all_duplicates(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        relative_file_path = _records_path(run_dir)
        existing = [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")]
        bluesky_storage.append_records(existing, relative_file_path)
        config = DedupeConfig(id_column="uri")
        dedupe_session = DedupeSession(config)
        dedupe_session.warm(bluesky_storage, relative_file_path)

        result = bluesky_storage.append_deduped_records(
            [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")],
            relative_file_path,
            dedupe_session=dedupe_session,
        )

        assert result.kept == 0
        assert result.skipped == 1
        assert len(bluesky_storage.load_seen_uris(relative_file_path)) == 1


class TestWriteRunMetadataAtomic:
    """Tests for StorageManager.write_run_metadata_atomic."""

    def test_write_run_metadata_atomic(self, bluesky_storage) -> None:
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
        payload = {"sync_status": "in_progress", "row_count": 0}

        bluesky_storage.write_run_metadata_atomic(run_dir, payload)
        metadata_path = resolve_package_path(run_dir) / "metadata.json"
        assert not (resolve_package_path(run_dir) / "metadata.json.tmp").exists()
        assert json.loads(metadata_path.read_text(encoding="utf-8")) == payload
