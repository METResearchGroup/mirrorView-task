from __future__ import annotations

import json

import pytest

from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.storage import (
    BlueskyStorageManager,
    RedditStorageManager,
    StorageStage,
    TwitterStorageManager,
)
from tests.data_platform.conftest import make_ingestion_row
from tests.data_platform.constants import (
    VALID_DATASET_ID,
    VALID_REDDIT_DATASET_ID,
    VALID_TWITTER_DATASET_ID,
)
from tests.data_platform.ingestion.reddit_conftest import mock_comment_row
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def test_bluesky_storage_root_includes_dataset_id(data_root, bluesky_storage) -> None:
    assert bluesky_storage.root_dir == data_root / "bluesky" / VALID_DATASET_ID / "raw"


def test_latest_run_dir_scoped_to_dataset(data_root, bluesky_storage) -> None:
    other_id = "bluesky_00000000-0000-4000-8000-000000000002"
    storage_b = BlueskyStorageManager(StorageStage.RAW, other_id)

    run_a = bluesky_storage.create_new_run_dir("2026_05_29-10:00:00")
    storage_b.create_new_run_dir("2026_05_29-11:00:00")

    assert bluesky_storage.latest_run_dir() == run_a


def test_append_records_writes_header_once(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")

    bluesky_storage.append_records([make_ingestion_row()], run_dir)
    second_row = make_ingestion_row(uri="at://did:plc:example/app.bsky.feed.post/def")
    bluesky_storage.append_records([second_row], run_dir)

    csv_path = run_dir / "posts.csv"
    lines = csv_path.read_text(encoding="utf-8").strip().splitlines()
    assert lines[0].startswith("uri,")
    assert len(lines) == 3


def test_load_seen_ids_from_disk(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
    row = make_ingestion_row()
    bluesky_storage.append_records([row], run_dir)

    assert bluesky_storage.load_seen_ids_from_disk(run_dir, "uri") == {row["uri"]}


def test_append_deduped_records_skips_current_run_duplicates(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
    existing = [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")]
    bluesky_storage.append_records(existing, run_dir)
    config = DedupeConfig(id_column="uri")
    dedupe_session = DedupeSession(config)
    dedupe_session.warm(bluesky_storage, run_dir)

    result = bluesky_storage.append_deduped_records(
        [
            make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1"),
            make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a2"),
        ],
        run_dir,
        dedupe_session=dedupe_session,
    )

    assert result.kept == 1
    assert result.skipped == 1
    assert bluesky_storage.load_seen_ids_from_disk(run_dir, "uri") == {
        "at://did:plc:ex/app.bsky.feed.post/a1",
        "at://did:plc:ex/app.bsky.feed.post/a2",
    }


def test_append_deduped_records_skips_prior_run_duplicates(data_root) -> None:
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    current_run = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
    comment_storage.append_records(
        [mock_comment_row("t1_comment_a")],
        current_run,
        filename="comments.csv",
    )
    config = DedupeConfig(id_column="comment_fullname", filename="comments.csv")
    dedupe_session = DedupeSession(config)
    dedupe_session.warm(comment_storage, current_run)

    result = comment_storage.append_deduped_records(
        [
            mock_comment_row("t1_comment_a"),
            mock_comment_row("t1_comment_b"),
        ],
        current_run,
        dedupe_session=dedupe_session,
        filename="comments.csv",
    )

    assert result.kept == 1
    assert result.skipped == 1
    assert comment_storage.load_seen_ids_from_disk(
        current_run, "comment_fullname", filename="comments.csv"
    ) == {"t1_comment_a", "t1_comment_b"}


def test_append_deduped_records_skips_ids_from_prior_run_dirs(bluesky_storage) -> None:
    prior_run = bluesky_storage.create_new_run_dir("2026_05_29-10:00:00")
    current_run = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
    prior_uri = "at://did:plc:ex/app.bsky.feed.post/prior"
    bluesky_storage.append_records([make_ingestion_row(uri=prior_uri)], prior_run)
    config = DedupeConfig(id_column="uri", include_prior_runs=True)
    dedupe_session = DedupeSession(config)
    dedupe_session.warm(bluesky_storage, current_run)

    result = bluesky_storage.append_deduped_records(
        [
            make_ingestion_row(uri=prior_uri),
            make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/new"),
        ],
        current_run,
        dedupe_session=dedupe_session,
    )

    assert result.kept == 1
    assert result.skipped == 1
    assert bluesky_storage.load_seen_ids_from_all_runs("uri") == {
        prior_uri,
        "at://did:plc:ex/app.bsky.feed.post/new",
    }


def test_append_deduped_records_does_not_dedupe_across_datasets(data_root) -> None:
    dataset_a = "reddit_00000000-0000-4000-8000-000000000001"
    dataset_b = "reddit_00000000-0000-4000-8000-000000000002"
    storage_a = RedditStorageManager(StorageStage.RAW, dataset_a)
    storage_b = RedditStorageManager(StorageStage.RAW, dataset_b)
    prior_run_a = storage_a.create_new_run_dir("2026_05_29-10:00:00")
    current_run_b = storage_b.create_new_run_dir("2026_05_30-10:00:00")
    storage_a.append_records(
        [mock_comment_row("t1_comment_a")],
        prior_run_a,
        filename="comments.csv",
    )
    config = DedupeConfig(id_column="comment_fullname", filename="comments.csv")
    dedupe_session = DedupeSession(config)
    dedupe_session.warm(storage_b, current_run_b)

    result = storage_b.append_deduped_records(
        [
            mock_comment_row("t1_comment_a"),
            mock_comment_row("t1_comment_b"),
        ],
        current_run_b,
        dedupe_session=dedupe_session,
        filename="comments.csv",
    )

    assert result.kept == 2
    assert result.skipped == 0


def test_append_deduped_records_returns_empty_when_all_duplicates(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
    existing = [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")]
    bluesky_storage.append_records(existing, run_dir)
    config = DedupeConfig(id_column="uri")
    dedupe_session = DedupeSession(config)
    dedupe_session.warm(bluesky_storage, run_dir)

    result = bluesky_storage.append_deduped_records(
        [make_ingestion_row(uri="at://did:plc:ex/app.bsky.feed.post/a1")],
        run_dir,
        dedupe_session=dedupe_session,
    )

    assert result.kept == 0
    assert result.skipped == 1
    assert len(bluesky_storage.load_seen_ids_from_disk(run_dir, "uri")) == 1


def test_write_run_metadata_atomic(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-10:00:00")
    payload = {"sync_status": "in_progress", "row_count": 0}

    bluesky_storage.write_run_metadata_atomic(run_dir, payload)
    metadata_path = run_dir / "metadata.json"
    assert not (run_dir / "metadata.json.tmp").exists()
    assert json.loads(metadata_path.read_text(encoding="utf-8")) == payload


def test_write_records_validates_rows(bluesky_storage) -> None:
    run_dir = bluesky_storage.create_new_run_dir("2026_05_30-11:00:00")
    with pytest.raises(Exception):
        bluesky_storage.write_records(
            [{"uri": "at://missing-fields"}],
            run_dir,
        )


class TestWriteRecordsAddsRecordId:
    """Tests for record_id generation during storage writes."""

    def test_bluesky_write_adds_record_id_from_uri(self, bluesky_storage) -> None:
        """Raw Bluesky writes persist bluesky_{sha256(uri)} without caller-supplied record_id."""
        run_dir = bluesky_storage.create_new_run_dir("2026_05_30-11:00:00")
        row = make_ingestion_row()
        row_without_record_id = {key: value for key, value in row.items() if key != "record_id"}
        expected_record_id = row["record_id"]

        bluesky_storage.write_records([row_without_record_id], run_dir)
        saved = bluesky_storage.load_records(run_dir=run_dir)

        assert saved.iloc[0]["record_id"] == expected_record_id

    def test_twitter_write_adds_record_id_from_tweet_id(self, data_root) -> None:
        """Raw Twitter writes persist twitter_{tweet_id}."""
        storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-11:00:00")
        row = mock_tweet_row("1000000000000000001")
        row_without_record_id = {key: value for key, value in row.items() if key != "record_id"}

        storage.write_records([row_without_record_id], run_dir)
        saved = storage.load_records(run_dir=run_dir)

        assert saved.iloc[0]["record_id"] == "twitter_1000000000000000001"

    def test_reddit_write_adds_record_id_from_comment_fullname(self, data_root) -> None:
        """Raw Reddit comment writes persist reddit_{comment_fullname}."""
        storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-11:00:00")
        row = mock_comment_row("t1_comment_a")
        row_without_record_id = {key: value for key, value in row.items() if key != "record_id"}

        storage.write_records([row_without_record_id], run_dir)
        saved = storage.load_records(run_dir=run_dir)

        assert saved.iloc[0]["record_id"] == "reddit_t1_comment_a"


class TestTwitterStorageManagerRecordsFilename:
    """Tests for TwitterStorageManager.records_filename."""

    def test_defaults_to_posts_csv_without_manifest(self, data_root) -> None:
        """Verifies Twitter storage uses posts.csv when no dataset.json exists."""
        storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
        expected = "posts.csv"

        result = storage.records_filename

        assert result == expected

    def test_uses_parquet_suffix_when_manifest_format_is_parquet(self, data_root) -> None:
        """Verifies Twitter storage restems posts to parquet from dataset.json."""
        write_dataset_manifest(
            "twitter",
            VALID_TWITTER_DATASET_ID,
            name="test",
            ingestion_config="data_platform/ingestion/configs/twitter/mirrorview.yaml",
            data_format=ValidDataFormats.PARQUET,
        )
        storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
        expected = "posts.parquet"

        result = storage.records_filename

        assert result == expected


class TestRedditStorageManagerRecordsFilename:
    """Tests for RedditStorageManager.records_filename."""

    def test_defaults_to_csv_names_without_manifest(self, data_root) -> None:
        """Verifies Reddit comment and post storage use csv names with no dataset.json."""
        comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
        post_storage = comment_storage.post_storage()

        assert comment_storage.records_filename == "comments.csv"
        assert post_storage.records_filename == "posts.csv"

    def test_uses_parquet_suffix_when_manifest_format_is_parquet(self, data_root) -> None:
        """Verifies Reddit storage restems comments and posts from dataset.json."""
        write_dataset_manifest(
            "reddit",
            VALID_REDDIT_DATASET_ID,
            name="test",
            ingestion_config="data_platform/ingestion/configs/reddit/mirrorview.yaml",
            data_format=ValidDataFormats.PARQUET,
        )
        comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
        post_storage = comment_storage.post_storage()
        expected_comments = "comments.parquet"
        expected_posts = "posts.parquet"

        result_comments = comment_storage.records_filename
        result_posts = post_storage.records_filename

        assert result_comments == expected_comments
        assert result_posts == expected_posts
