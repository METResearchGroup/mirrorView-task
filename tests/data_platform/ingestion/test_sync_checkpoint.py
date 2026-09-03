from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from data_platform.ingestion.sync_checkpoint import (
    COMMENTS_DEDUPE_POLICY_KEY,
    ROWS_SKIPPED_AS_DUPLICATES_KEY,
    SKIPPED_BY_RECORD_TYPE_KEY,
    SyncStatus,
    TaskStatus,
    build_base_sync_metadata,
    ensure_dataset_manifest,
    find_resume_run_dir,
    flush_run_metadata,
    get_task_progress,
    increment_duplicate_skip_counters,
    load_checkpoint_run,
    mark_remaining_tasks_skipped,
    mark_task_completed,
    parse_max_comments,
    parse_max_posts,
    record_type_to_filename,
    require_dataset_id,
    require_latest_in_progress_run_dir,
    resolve_dedupe_policy,
    resolve_limit_per_task,
    start_new_sync_run,
    stop_at_record_cap,
    sync_status_from_tasks,
    validate_tasks_for_resume,
)
from data_platform.utils.dataset import load_dataset_manifest
from data_platform.utils.deduplication import DedupeConfig, DedupeSession, PRIOR_RUN_POLICY
from data_platform.utils.storage import BlueskyStorageManager, StorageStage, TwitterStorageManager
from lib.constants import REPO_ROOT
from tests.data_platform.constants import VALID_DATASET_ID, VALID_TWITTER_DATASET_ID
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row

BLUESKY_MIRRORVIEW_CONFIG = (
    REPO_ROOT / "data_platform" / "ingestion" / "configs" / "bluesky" / "mirrorview.yaml"
)
TWITTER_MIRRORVIEW_CONFIG = (
    REPO_ROOT / "data_platform" / "ingestion" / "configs" / "twitter" / "mirrorview.yaml"
)
EXPECTED_BLUESKY_RELATIVE = "data_platform/ingestion/configs/bluesky/mirrorview.yaml"
EXPECTED_TWITTER_RELATIVE = "data_platform/ingestion/configs/twitter/mirrorview.yaml"


@dataclass(frozen=True)
class _StubTask:
    task_id: str


def _twitter_sync_config() -> dict:
    return {
        "dataset_id": VALID_TWITTER_DATASET_ID,
        "name": "test",
        "description": "desc",
        "date": "2026-05-31",
        "record_types": ["twitter.tweet"],
        "ingestion_params": {},
    }


def test_get_task_progress_missing_tasks_raises_key_error() -> None:
    with pytest.raises(KeyError):
        get_task_progress({})


def test_validate_tasks_for_resume_mismatch_raises_value_error() -> None:
    metadata = {
        "tasks": {
            "alpha": {"status": TaskStatus.PENDING.value},
            "extra": {"status": TaskStatus.PENDING.value},
        }
    }
    tasks = [_StubTask("alpha"), _StubTask("beta")]
    with pytest.raises(ValueError, match="missing in metadata"):
        validate_tasks_for_resume(tasks, metadata, entity_label="keywords")


def test_validate_tasks_for_resume_matching_tasks_passes() -> None:
    metadata = {
        "tasks": {
            "alpha": {"status": TaskStatus.PENDING.value},
            "beta": {"status": TaskStatus.PENDING.value},
        }
    }
    tasks = [_StubTask("alpha"), _StubTask("beta")]
    validate_tasks_for_resume(tasks, metadata, entity_label="keywords")


def test_mark_remaining_tasks_skipped() -> None:
    progress = {
        "a": {"status": TaskStatus.PENDING.value},
        "b": {"status": TaskStatus.COMPLETED.value},
        "c": {"status": TaskStatus.IN_PROGRESS.value},
    }
    mark_remaining_tasks_skipped(progress)
    assert progress["a"]["status"] == TaskStatus.SKIPPED.value
    assert progress["b"]["status"] == TaskStatus.COMPLETED.value
    assert progress["c"]["status"] == TaskStatus.IN_PROGRESS.value


def test_sync_status_from_tasks_all_done() -> None:
    progress = {
        "a": {"status": TaskStatus.COMPLETED.value},
        "b": {"status": TaskStatus.SKIPPED.value},
    }
    assert sync_status_from_tasks(progress) == SyncStatus.COMPLETED


def test_sync_status_from_tasks_still_in_progress() -> None:
    progress = {
        "a": {"status": TaskStatus.COMPLETED.value},
        "b": {"status": TaskStatus.PENDING.value},
    }
    assert sync_status_from_tasks(progress) == SyncStatus.IN_PROGRESS


def test_require_dataset_id_missing_raises() -> None:
    with pytest.raises(ValueError, match="dataset_id"):
        require_dataset_id({}, platform="twitter")


def test_record_type_to_filename_known_types() -> None:
    assert record_type_to_filename("app.bsky.feed.post") == "posts.csv"
    assert record_type_to_filename("reddit.comment") == "comments.csv"
    assert record_type_to_filename("custom.record") == "record.csv"


def test_build_base_sync_metadata_includes_tasks() -> None:
    config = _twitter_sync_config()
    metadata = build_base_sync_metadata(
        config,
        TWITTER_MIRRORVIEW_CONFIG,
        "2026_05_30-10:00:00",
        [_StubTask("alpha")],
        task_progress_builder=lambda task: {"status": TaskStatus.PENDING.value, "id": task.task_id},
        extra_fields={"post_row_count": 0},
    )
    assert metadata["sync_status"] == SyncStatus.IN_PROGRESS.value
    assert metadata["tasks"]["alpha"]["status"] == TaskStatus.PENDING.value
    assert metadata["post_row_count"] == 0


def test_find_resume_run_dir_specific_run(data_root) -> None:
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    flush_run_metadata(storage, run_dir, {"sync_status": SyncStatus.IN_PROGRESS.value, "tasks": {}})
    assert find_resume_run_dir(storage, run_dir_name="2026_05_30-10:00:00") == run_dir


def test_find_resume_run_dir_latest_in_progress(data_root) -> None:
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    older = storage.create_new_run_dir("2026_05_30-09:00:00")
    newer = storage.create_new_run_dir("2026_05_30-10:00:00")
    flush_run_metadata(storage, older, {"sync_status": SyncStatus.COMPLETED.value, "tasks": {}})
    flush_run_metadata(storage, newer, {"sync_status": SyncStatus.IN_PROGRESS.value, "tasks": {}})
    assert find_resume_run_dir(storage, run_dir_name=None) == newer


PATCHED_SYNC_TIMESTAMP = "2026_05_30-11:00:00"


def _new_run_metadata(sync_timestamp: str) -> dict[str, Any]:
    return {
        "sync_status": SyncStatus.IN_PROGRESS.value,
        "sync_timestamp": sync_timestamp,
        "tasks": {"alpha": {"status": TaskStatus.PENDING.value}},
    }


def _matching_stub_tasks() -> list[_StubTask]:
    return [_StubTask("alpha")]


class TestStartNewSyncRun:
    """Tests for start_new_sync_run()."""

    def test_creates_run_when_dataset_has_no_raw_runs(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        monkeypatch.setattr(
            "data_platform.ingestion.sync_checkpoint.get_current_timestamp",
            lambda: PATCHED_SYNC_TIMESTAMP,
        )

        result_dir, result_metadata = start_new_sync_run(storage, _new_run_metadata)

        expected_dir = storage.root_dir / PATCHED_SYNC_TIMESTAMP
        expected_metadata = _new_run_metadata(PATCHED_SYNC_TIMESTAMP)
        assert result_dir == expected_dir
        assert result_metadata == expected_metadata
        assert storage.load_run_metadata(result_dir) == expected_metadata

    def test_raises_when_unfinished_run_exists(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        existing = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            existing,
            {"sync_status": SyncStatus.IN_PROGRESS.value, "tasks": {}},
        )
        before = {path.name for path in storage.root_dir.iterdir() if path.is_dir()}

        with pytest.raises(ValueError, match="unfinished"):
            start_new_sync_run(storage, _new_run_metadata)

        after = {path.name for path in storage.root_dir.iterdir() if path.is_dir()}
        assert after == before

    def test_creates_run_when_only_completed_runs_exist(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        completed = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            completed,
            {"sync_status": SyncStatus.COMPLETED.value, "tasks": {}},
        )
        monkeypatch.setattr(
            "data_platform.ingestion.sync_checkpoint.get_current_timestamp",
            lambda: PATCHED_SYNC_TIMESTAMP,
        )

        result_dir, result_metadata = start_new_sync_run(storage, _new_run_metadata)

        expected_dir = storage.root_dir / PATCHED_SYNC_TIMESTAMP
        assert result_dir == expected_dir
        assert result_metadata["sync_timestamp"] == PATCHED_SYNC_TIMESTAMP
        assert completed.is_dir()


class TestLoadCheckpointRun:
    """Tests for load_checkpoint_run()."""

    def test_returns_unfinished_named_run(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
        metadata = {
            "sync_status": SyncStatus.IN_PROGRESS.value,
            "tasks": {"alpha": {"status": TaskStatus.PENDING.value}},
        }
        flush_run_metadata(storage, run_dir, metadata)

        result_dir, result_metadata = load_checkpoint_run(
            storage,
            _matching_stub_tasks(),
            "2026_05_30-10:00:00",
            "keywords",
        )

        assert result_dir == run_dir
        assert result_metadata["sync_status"] == SyncStatus.IN_PROGRESS.value
        assert result_metadata["tasks"]["alpha"]["status"] == TaskStatus.PENDING.value

    def test_raises_when_directory_is_missing(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)

        with pytest.raises(FileNotFoundError):
            load_checkpoint_run(
                storage,
                _matching_stub_tasks(),
                "2026_05_30-10:00:00",
                "keywords",
            )

    def test_raises_when_run_is_completed(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
        metadata = {
            "sync_status": SyncStatus.COMPLETED.value,
            "tasks": {"alpha": {"status": TaskStatus.COMPLETED.value}},
        }
        flush_run_metadata(storage, run_dir, metadata)

        with pytest.raises(ValueError, match="completed"):
            load_checkpoint_run(
                storage,
                _matching_stub_tasks(),
                "2026_05_30-10:00:00",
                "keywords",
            )

        assert storage.load_run_metadata(run_dir)["sync_status"] == SyncStatus.COMPLETED.value

    def test_raises_when_tasks_do_not_match(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            run_dir,
            {
                "sync_status": SyncStatus.IN_PROGRESS.value,
                "tasks": {
                    "alpha": {"status": TaskStatus.PENDING.value},
                    "extra": {"status": TaskStatus.PENDING.value},
                },
            },
        )

        with pytest.raises(ValueError, match="missing in metadata"):
            load_checkpoint_run(
                storage,
                _matching_stub_tasks(),
                "2026_05_30-10:00:00",
                "keywords",
            )


class TestRequireLatestInProgressRunDir:
    """Tests for require_latest_in_progress_run_dir()."""

    def test_returns_newest_unfinished_run(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        older = storage.create_new_run_dir("2026_05_30-09:00:00")
        newer = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            older,
            {"sync_status": SyncStatus.COMPLETED.value, "tasks": {}},
        )
        flush_run_metadata(
            storage,
            newer,
            {"sync_status": SyncStatus.IN_PROGRESS.value, "tasks": {}},
        )

        result = require_latest_in_progress_run_dir(storage)

        expected = newer
        assert result == expected

    def test_raises_when_only_completed_runs_exist(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        completed = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            completed,
            {"sync_status": SyncStatus.COMPLETED.value, "tasks": {}},
        )

        with pytest.raises(FileNotFoundError, match="unfinished"):
            require_latest_in_progress_run_dir(storage)

    def test_raises_when_no_runs_exist(self, data_root) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)

        with pytest.raises(FileNotFoundError, match="unfinished"):
            require_latest_in_progress_run_dir(storage)


def test_mark_task_completed_updates_entry_and_metadata(data_root) -> None:
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = {"row_count": 0, "tasks": {"alpha": {"status": TaskStatus.PENDING.value}}}
    entry = metadata["tasks"]["alpha"]

    mark_task_completed(
        entry,
        storage,
        run_dir,
        metadata,
        entry_updates={"pages_fetched": 2, "rows_collected": 5},
        metadata_updates={"row_count": 5},
    )

    assert entry["status"] == TaskStatus.COMPLETED.value
    assert entry["last_error"] is None
    assert entry["pages_fetched"] == 2
    assert metadata["row_count"] == 5
    assert (
        storage.load_run_metadata(run_dir)["tasks"]["alpha"]["status"] == TaskStatus.COMPLETED.value
    )


def test_stop_at_record_cap_marks_pending_skipped(data_root) -> None:
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = {
        "row_count": 10,
        "tasks": {
            "a": {"status": TaskStatus.PENDING.value},
            "b": {"status": TaskStatus.COMPLETED.value},
        },
    }
    assert stop_at_record_cap(metadata, storage, run_dir, 10) is True
    assert metadata["tasks"]["a"]["status"] == TaskStatus.SKIPPED.value


def test_append_deduped_records_skips_seen_ids(data_root) -> None:
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    existing = [mock_tweet_row("1")]
    storage.append_records(existing, run_dir)
    config = DedupeConfig(id_column="tweet_id")
    dedupe_session = DedupeSession(config)
    dedupe_session.load_seen_ids(storage, run_dir)
    incoming = [mock_tweet_row("1"), mock_tweet_row("2")]
    result = storage.append_deduped_records(incoming, run_dir, dedupe_session=dedupe_session)
    assert result.skipped == 1
    assert result.kept == 1
    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {"1", "2"}


class TestBuildBaseSyncMetadata:
    """Tests for build_base_sync_metadata()."""

    def test_stores_repo_relative_bluesky_config_path(self) -> None:
        """Verifies run metadata stores the Bluesky YAML as a repo-relative POSIX path."""
        config = _twitter_sync_config()
        config["dataset_id"] = VALID_DATASET_ID
        expected = EXPECTED_BLUESKY_RELATIVE

        result = build_base_sync_metadata(
            config,
            BLUESKY_MIRRORVIEW_CONFIG,
            "2026_05_30-10:00:00",
            [_StubTask("alpha")],
            task_progress_builder=lambda task: {
                "status": TaskStatus.PENDING.value,
                "id": task.task_id,
            },
        )

        assert result["ingestion_config"] == expected

    def test_same_basename_twitter_config_stays_distinct(self) -> None:
        """Verifies a Twitter YAML with the same file name is not stored as the Bluesky path."""
        config = _twitter_sync_config()
        expected = EXPECTED_TWITTER_RELATIVE

        result = build_base_sync_metadata(
            config,
            TWITTER_MIRRORVIEW_CONFIG,
            "2026_05_30-10:00:00",
            [_StubTask("alpha")],
            task_progress_builder=lambda task: {
                "status": TaskStatus.PENDING.value,
                "id": task.task_id,
            },
        )

        assert result["ingestion_config"] == expected
        assert result["ingestion_config"] != EXPECTED_BLUESKY_RELATIVE


class TestEnsureDatasetManifest:
    """Tests for ensure_dataset_manifest()."""

    def test_stores_repo_relative_config_path(self, data_root) -> None:
        """Verifies a new dataset manifest stores the repo-relative POSIX config path."""
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        config = {"name": "mirrorview"}
        expected = EXPECTED_BLUESKY_RELATIVE

        ensure_dataset_manifest(
            storage,
            "bluesky",
            VALID_DATASET_ID,
            config,
            BLUESKY_MIRRORVIEW_CONFIG,
        )
        result = load_dataset_manifest("bluesky", VALID_DATASET_ID)

        assert result["ingestion_config"] == expected

    def test_matches_run_metadata_config_path(self, data_root) -> None:
        """Verifies run metadata and the dataset manifest store the same config path."""
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        config = _twitter_sync_config()
        config["dataset_id"] = VALID_DATASET_ID
        expected = EXPECTED_BLUESKY_RELATIVE

        metadata = build_base_sync_metadata(
            config,
            BLUESKY_MIRRORVIEW_CONFIG,
            "2026_05_30-10:00:00",
            [_StubTask("alpha")],
            task_progress_builder=lambda task: {
                "status": TaskStatus.PENDING.value,
                "id": task.task_id,
            },
        )
        ensure_dataset_manifest(
            storage,
            "bluesky",
            VALID_DATASET_ID,
            {"name": "mirrorview"},
            BLUESKY_MIRRORVIEW_CONFIG,
        )
        manifest = load_dataset_manifest("bluesky", VALID_DATASET_ID)

        assert metadata["ingestion_config"] == expected
        assert manifest["ingestion_config"] == expected
        assert metadata["ingestion_config"] == manifest["ingestion_config"]


class TestResolveLimitPerTask:
    """Tests for resolve_limit_per_task()."""

    def test_returns_limit_per_task_when_present(self) -> None:
        ingestion_params = {"limit_per_task": 7}
        expected = 7

        result = resolve_limit_per_task(ingestion_params)

        assert result == expected

    def test_accepts_zero_limit_per_task(self) -> None:
        ingestion_params = {"limit_per_task": 0}
        expected = 0

        result = resolve_limit_per_task(ingestion_params)

        assert result == expected

    def test_missing_limit_per_task_raises_key_error(self) -> None:
        with pytest.raises(KeyError):
            resolve_limit_per_task({})


class TestParseMaxPosts:
    """Tests for parse_max_posts()."""

    def test_prefers_max_posts(self) -> None:
        ingestion_params = {"max_posts": 7}
        expected = 7

        result = parse_max_posts(ingestion_params)

        assert result == expected

    def test_accepts_zero_max_posts(self) -> None:
        ingestion_params = {"max_posts": 0}
        expected = 0

        result = parse_max_posts(ingestion_params)

        assert result == expected

    def test_returns_none_when_unset(self) -> None:
        ingestion_params: dict[str, Any] = {}
        expected = None

        result = parse_max_posts(ingestion_params)

        assert result == expected

    def test_returns_none_when_primary_is_explicit_none(self) -> None:
        ingestion_params = {"max_posts": None}
        expected = None

        result = parse_max_posts(ingestion_params)

        assert result == expected

    def test_ignores_max_comments(self) -> None:
        ingestion_params = {"max_comments": 9}
        expected = None

        result = parse_max_posts(ingestion_params)

        assert result == expected


class TestParseMaxComments:
    """Tests for parse_max_comments()."""

    def test_prefers_max_comments(self) -> None:
        ingestion_params = {"max_comments": 8}
        expected = 8

        result = parse_max_comments(ingestion_params)

        assert result == expected

    def test_accepts_zero_max_comments(self) -> None:
        ingestion_params = {"max_comments": 0}
        expected = 0

        result = parse_max_comments(ingestion_params)

        assert result == expected

    def test_returns_none_when_unset(self) -> None:
        ingestion_params: dict[str, Any] = {}
        expected = None

        result = parse_max_comments(ingestion_params)

        assert result == expected

    def test_ignores_max_posts(self) -> None:
        ingestion_params = {"max_posts": 7}
        expected = None

        result = parse_max_comments(ingestion_params)

        assert result == expected


class TestResolveDedupePolicy:
    """Tests for resolve_dedupe_policy()."""

    def test_returns_shared_policy_when_set(self) -> None:
        ingestion_params = {"dedupe_policy": [PRIOR_RUN_POLICY]}
        expected = [PRIOR_RUN_POLICY]

        result = resolve_dedupe_policy(ingestion_params)

        assert result == expected

    def test_returns_none_when_unset(self) -> None:
        ingestion_params: dict[str, Any] = {}
        expected = None

        result = resolve_dedupe_policy(ingestion_params)

        assert result is expected

    def test_ignores_type_keys(self) -> None:
        ingestion_params = {COMMENTS_DEDUPE_POLICY_KEY: [PRIOR_RUN_POLICY]}
        expected = None

        result = resolve_dedupe_policy(ingestion_params)

        assert result is expected


BLUESKY_POST_RECORD_TYPE = "app.bsky.feed.post"


class TestIncrementDuplicateSkipCounters:
    """Tests for increment_duplicate_skip_counters()."""

    def test_writes_canonical_keys_on_empty_metadata(self) -> None:
        metadata: dict[str, Any] = {}
        expected_total = 2
        expected_breakdown = {BLUESKY_POST_RECORD_TYPE: 2}

        increment_duplicate_skip_counters(
            metadata,
            record_type=BLUESKY_POST_RECORD_TYPE,
            skipped=2,
        )

        assert metadata[ROWS_SKIPPED_AS_DUPLICATES_KEY] == expected_total
        assert metadata[SKIPPED_BY_RECORD_TYPE_KEY] == expected_breakdown

    def test_adds_to_existing_canonical_keys(self) -> None:
        metadata = {
            ROWS_SKIPPED_AS_DUPLICATES_KEY: 3,
            SKIPPED_BY_RECORD_TYPE_KEY: {BLUESKY_POST_RECORD_TYPE: 3},
        }
        expected_total = 4
        expected_breakdown = {BLUESKY_POST_RECORD_TYPE: 4}

        increment_duplicate_skip_counters(
            metadata,
            record_type=BLUESKY_POST_RECORD_TYPE,
            skipped=1,
        )

        assert metadata[ROWS_SKIPPED_AS_DUPLICATES_KEY] == expected_total
        assert metadata[SKIPPED_BY_RECORD_TYPE_KEY] == expected_breakdown
