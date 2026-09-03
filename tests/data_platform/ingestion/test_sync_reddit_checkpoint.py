from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from data_platform.ingestion import sync_reddit
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.deduplication import PRIOR_RUN_POLICY
from data_platform.utils.storage import RedditStorageManager, StorageStage
from tests.data_platform.constants import TEST_INGEST_CONFIG_PATH, VALID_REDDIT_DATASET_ID
from tests.data_platform.ingestion.reddit_conftest import (
    minimal_reddit_sync_config,
    mock_comment_row,
)


def test_init_sync_metadata_subreddit_task_ledger() -> None:
    config = minimal_reddit_sync_config()
    sync_tasks = sync_reddit.build_sync_tasks(config["ingestion_params"])
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    assert metadata["sync_status"] == "in_progress"
    assert set(metadata["tasks"]) == {"alphasub", "betasub"}
    assert metadata["tasks"]["alphasub"]["status"] == "pending"
    assert metadata["tasks"]["alphasub"]["kind"] == "reddit"
    assert "post_row_count" not in metadata
    assert "posts_collected" not in metadata["tasks"]["alphasub"]


def test_run_sync_tasks_appends_per_subreddit(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    rows_by_subreddit = {
        "AlphaSub": [mock_comment_row("t1_comment_a1")],
        "BetaSub": [mock_comment_row("t1_comment_b1")],
    }

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        comment_rows = rows_by_subreddit[subreddit]
        stats = {
            "subreddit": subreddit,
            "listing": fetch_cfg.get("listing", "hot"),
            "listing_time_filter": None,
            "limit_per_subreddit": fetch_cfg["limit_per_task"],
            "submissions_scanned": 1,
            "comments_collected": len(comment_rows),
        }
        return sync_reddit.SubredditFetchResult(
            comment_rows=comment_rows,
            stats=stats,
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
    )

    assert metadata["tasks"]["alphasub"]["status"] == "completed"
    assert metadata["tasks"]["betasub"]["status"] == "completed"
    assert metadata["row_count"] == 2
    assert "post_row_count" not in metadata
    assert (run_dir / "comments.csv").exists()
    assert not (run_dir / "posts.csv").exists()
    assert not (run_dir / "comments.parquet").exists()
    assert not (run_dir / "posts.parquet").exists()
    assert len(storage.load_seen_ids_from_disk(run_dir, "comment_fullname")) == 2


def _run_two_subreddit_comment_sync(
    monkeypatch: pytest.MonkeyPatch,
    ingestion_params: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    rows_by_subreddit = {
        "AlphaSub": [mock_comment_row("t1_comment_a1")],
        "BetaSub": [mock_comment_row("t1_comment_b1")],
    }

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        comment_rows = rows_by_subreddit[subreddit]
        stats = {
            "subreddit": subreddit,
            "listing": fetch_cfg.get("listing", "hot"),
            "listing_time_filter": None,
            "limit_per_subreddit": fetch_cfg["limit_per_task"],
            "submissions_scanned": 1,
            "comments_collected": len(comment_rows),
        }
        return sync_reddit.SubredditFetchResult(
            comment_rows=comment_rows,
            stats=stats,
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
    )
    return metadata


def test_run_sync_tasks_caps_comments_by_max_comments(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = dict(config["ingestion_params"])
    ingestion_params["max_comments"] = 1
    metadata = _run_two_subreddit_comment_sync(
        monkeypatch, ingestion_params, config
    )

    assert metadata["row_count"] == 1
    assert metadata["tasks"]["alphasub"]["status"] == "completed"
    assert metadata["tasks"]["betasub"]["status"] == "skipped"


def test_run_sync_tasks_skips_prior_run_comments(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["comments_dedupe_policy"] = ["current_run", PRIOR_RUN_POLICY]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)

    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    storage.append_records(
        [mock_comment_row("t1_comment_old")],
        run_dir,
    )
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        return sync_reddit.SubredditFetchResult(
            comment_rows=[
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            stats={
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "listing_time_filter": None,
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "submissions_scanned": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
    )

    seen = storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
    assert seen == {"t1_comment_old", "t1_comment_new"}
    assert metadata["rows_skipped_as_duplicates"] == 1
    assert metadata["skipped_as_duplicates_by_record_type"]["reddit.comment"] == 1
    assert "comments_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_skips_ids_from_other_dataset(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "reddit_00000000-0000-4000-8000-000000000002"
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    other_storage = RedditStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [mock_comment_row("t1_comment_old")],
        other_run,
    )

    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        return sync_reddit.SubredditFetchResult(
            comment_rows=[
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            stats={
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "listing_time_filter": None,
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "submissions_scanned": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
    )

    seen = storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
    assert seen == {"t1_comment_old", "t1_comment_new"}
    assert metadata["rows_skipped_as_duplicates"] == 0
    assert metadata["skipped_as_duplicates_by_record_type"].get("reddit.comment", 0) == 0
    assert "comments_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_respects_current_run_only_policy(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "reddit_00000000-0000-4000-8000-000000000002"
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["comments_dedupe_policy"] = ["current_run"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    other_storage = RedditStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [mock_comment_row("t1_comment_old")],
        other_run,
    )

    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        return sync_reddit.SubredditFetchResult(
            comment_rows=[mock_comment_row("t1_comment_old")],
            stats={
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "listing_time_filter": None,
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "submissions_scanned": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
    )

    seen = storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
    assert seen == {"t1_comment_old"}
    assert metadata.get("rows_skipped_as_duplicates", 0) == 0
    assert "comments_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_uses_shared_dedupe_policy_for_comments(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params.pop("comments_dedupe_policy", None)
    ingestion_params["dedupe_policy"] = [PRIOR_RUN_POLICY]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)

    prior_run = storage.create_new_run_dir("2026_05_29-10:00:00")
    storage.append_records(
        [mock_comment_row("t1_comment_old")],
        prior_run,
    )
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        return sync_reddit.SubredditFetchResult(
            comment_rows=[
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            stats={
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "listing_time_filter": None,
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "submissions_scanned": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
    )

    seen = storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
    assert seen == {"t1_comment_new"}
    assert metadata["rows_skipped_as_duplicates"] == 1
    assert metadata["skipped_as_duplicates_by_record_type"]["reddit.comment"] == 1
    assert "comments_skipped_as_duplicates" not in metadata


def test_resume_skips_completed_subreddits(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    metadata["tasks"]["alphasub"]["status"] = "completed"
    metadata["tasks"]["alphasub"]["comments_collected"] = 1
    storage.append_records(
        [mock_comment_row("t1_comment_a1")],
        run_dir,
    )
    metadata["row_count"] = 1
    storage.write_run_metadata_atomic(run_dir, metadata)

    calls: list[str] = []

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        calls.append(subreddit)
        return sync_reddit.SubredditFetchResult(
            comment_rows=[mock_comment_row("t1_comment_b1")],
            stats={
                "subreddit": subreddit,
                "listing": "hot",
                "listing_time_filter": None,
                "limit_per_subreddit": 2,
                "submissions_scanned": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    resumed_metadata = storage.load_run_metadata(run_dir)
    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        resumed_metadata,
        sync_tasks,
    )

    assert calls == ["BetaSub"]
    assert resumed_metadata["tasks"]["betasub"]["status"] == "completed"
    assert resumed_metadata["row_count"] == 2


def test_build_sync_tasks_strips_r_prefix() -> None:
    tasks = sync_reddit.build_sync_tasks({"subreddits": ["r/Politics"]})
    assert len(tasks) == 1
    assert tasks[0].task_id == "politics"
    assert tasks[0].subreddit == "Politics"


def test_build_sync_tasks_rejects_duplicate_normalized_subreddits() -> None:
    with pytest.raises(ValueError, match="Duplicate subreddit task_id"):
        sync_reddit.build_sync_tasks({"subreddits": ["r/politics", "politics"]})


def test_run_sync_tasks_writes_parquet_when_storage_format_is_parquet(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies the Reddit write loop stores parquet names for a parquet dataset."""
    write_dataset_manifest(
        "reddit",
        VALID_REDDIT_DATASET_ID,
        name="test",
        ingestion_config="data_platform/ingestion/configs/reddit/mirrorview.yaml",
        data_format=ValidDataFormats.PARQUET,
    )
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
    ) -> sync_reddit.SubredditFetchResult:
        return sync_reddit.SubredditFetchResult(
            comment_rows=[mock_comment_row("t1_comment_a1")],
            stats={
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "listing_time_filter": None,
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "submissions_scanned": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
    )

    assert storage.records_filename == "comments.parquet"
    assert (run_dir / "comments.parquet").exists()
    assert not (run_dir / "posts.parquet").exists()
    assert not (run_dir / "comments.csv").exists()
    assert not (run_dir / "posts.csv").exists()


class TestSyncRecords:
    """Tests for sync_records."""

    def test_rebuilds_storage_after_parquet_manifest(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifies sync_records hands parquet storage into the write loop."""
        config = minimal_reddit_sync_config()
        config["output_format"] = "parquet"
        monkeypatch.setattr(sync_reddit, "load_config", lambda path: config)
        init_client = MagicMock(name="init_reddit_client")
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_reddit, "init_reddit_client", init_client)
        monkeypatch.setattr(sync_reddit, "run_sync_tasks", run_tasks)
        expected_comments = "comments.parquet"

        sync_reddit.sync_records(TEST_INGEST_CONFIG_PATH)
        storage = run_tasks.call_args.args[3]
        result_comments = storage.records_filename

        assert init_client.called is True
        assert result_comments == expected_comments
        assert len(run_tasks.call_args.args) == 6

    def test_raises_when_reddit_post_record_type_is_present(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """sync_records rejects configs that still name reddit.post."""
        config = minimal_reddit_sync_config()
        config["record_types"] = [
            sync_reddit.COMMENTS_RECORD_TYPE,
            "reddit.post",
        ]
        monkeypatch.setattr(sync_reddit, "load_config", lambda path: config)
        monkeypatch.setattr(sync_reddit, "init_reddit_client", MagicMock())
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_reddit, "run_sync_tasks", run_tasks)

        with pytest.raises(ValueError, match="record types"):
            sync_reddit.sync_records(TEST_INGEST_CONFIG_PATH)

        assert run_tasks.called is False

    def test_raises_when_comment_record_type_is_missing(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """sync_records rejects configs that omit reddit.comment."""
        config = minimal_reddit_sync_config()
        config["record_types"] = []
        monkeypatch.setattr(sync_reddit, "load_config", lambda path: config)
        monkeypatch.setattr(sync_reddit, "init_reddit_client", MagicMock())
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_reddit, "run_sync_tasks", run_tasks)

        with pytest.raises(ValueError, match="record types"):
            sync_reddit.sync_records(TEST_INGEST_CONFIG_PATH)

        assert run_tasks.called is False

    def test_raises_when_comment_record_type_is_missing(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """sync_records rejects configs that omit reddit.comment."""
        config = minimal_reddit_sync_config()
        config["record_types"] = []
        monkeypatch.setattr(sync_reddit, "load_config", lambda path: config)
        monkeypatch.setattr(sync_reddit, "init_reddit_client", MagicMock())
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_reddit, "run_sync_tasks", run_tasks)

        with pytest.raises(ValueError, match="record types"):
            sync_reddit.sync_records(TEST_INGEST_CONFIG_PATH)

        assert run_tasks.called is False


class TestFetchRecordsForSubredditLimitPerTask:
    """Tests that fetch_records_for_subreddit reads limit_per_task."""

    def test_passes_limit_per_task_to_listing_fetch(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ingestion_params = {"limit_per_task": 1}
        expected = 1
        captured: dict[str, int] = {}

        def fake_page(
            reddit: Any,
            subreddit: str,
            listing: str,
            limit: int,
            *,
            time_filter: str | None = None,
        ):
            captured["limit"] = limit
            return []

        monkeypatch.setattr(sync_reddit, "_fetch_subreddit_page", fake_page)

        sync_reddit.fetch_records_for_subreddit(
            MagicMock(),
            ingestion_params,
            "politics",
            sync_timestamp="2026_05_30-10:00:00",
        )
        result = captured["limit"]

        assert result == expected
