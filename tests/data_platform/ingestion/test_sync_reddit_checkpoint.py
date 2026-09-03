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
    mock_post_row,
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


def test_run_sync_tasks_appends_per_subreddit(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    rows_by_subreddit = {
        "AlphaSub": (
            [mock_post_row("t3_post_a1")],
            [mock_comment_row("t1_comment_a1")],
        ),
        "BetaSub": (
            [mock_post_row("t3_post_b1")],
            [mock_comment_row("t1_comment_b1")],
        ),
    }

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
        include_posts: bool,
        include_comments: bool,
    ):
        post_rows, comment_rows = rows_by_subreddit[subreddit]
        stats = {
            "subreddit": subreddit,
            "listing": fetch_cfg.get("listing", "hot"),
            "limit_per_subreddit": fetch_cfg["limit_per_task"],
            "posts_collected": len(post_rows),
            "comments_collected": len(comment_rows),
        }
        return post_rows, comment_rows, stats

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks,
        include_comments=True,
        include_posts=True,
    )

    assert metadata["tasks"]["alphasub"]["status"] == "completed"
    assert metadata["tasks"]["betasub"]["status"] == "completed"
    assert metadata["row_count"] == 2
    assert metadata["post_row_count"] == 2
    assert (run_dir / "comments.csv").exists()
    assert (run_dir / "posts.csv").exists()
    assert not (run_dir / "comments.parquet").exists()
    assert not (run_dir / "posts.parquet").exists()
    assert len(comment_storage.load_seen_ids_from_disk(run_dir, "comment_fullname")) == 2


def _run_two_subreddit_comment_sync(
    monkeypatch: pytest.MonkeyPatch,
    ingestion_params: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    rows_by_subreddit = {
        "AlphaSub": (
            [mock_post_row("t3_post_a1")],
            [mock_comment_row("t1_comment_a1")],
        ),
        "BetaSub": (
            [mock_post_row("t3_post_b1")],
            [mock_comment_row("t1_comment_b1")],
        ),
    }

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
        include_posts: bool,
        include_comments: bool,
    ):
        post_rows, comment_rows = rows_by_subreddit[subreddit]
        stats = {
            "subreddit": subreddit,
            "listing": fetch_cfg.get("listing", "hot"),
            "limit_per_subreddit": fetch_cfg["limit_per_task"],
            "posts_collected": len(post_rows),
            "comments_collected": len(comment_rows),
        }
        return post_rows, comment_rows, stats

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks,
        include_comments=True,
        include_posts=True,
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
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()

    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
    comment_storage.append_records(
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [mock_post_row("t3_post_a1")],
            [
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    seen = comment_storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
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

    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [mock_post_row("t3_post_a1")],
            [
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    seen = comment_storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
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

    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [mock_post_row("t3_post_a1")],
            [mock_comment_row("t1_comment_old")],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    seen = comment_storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
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
    ingestion_params.pop("posts_dedupe_policy", None)
    ingestion_params["dedupe_policy"] = [PRIOR_RUN_POLICY]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()

    prior_run = comment_storage.create_new_run_dir("2026_05_29-10:00:00")
    comment_storage.append_records(
        [mock_comment_row("t1_comment_old")],
        prior_run,
    )
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [mock_post_row("t3_post_a1")],
            [
                mock_comment_row("t1_comment_old"),
                mock_comment_row("t1_comment_new"),
            ],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 1,
                "comments_collected": 2,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    seen = comment_storage.load_seen_ids_from_disk(run_dir, "comment_fullname")
    assert seen == {"t1_comment_new"}
    assert metadata["rows_skipped_as_duplicates"] == 1
    assert metadata["skipped_as_duplicates_by_record_type"]["reddit.comment"] == 1
    assert "comments_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_empty_posts_override_does_not_skip_prior_posts(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params.pop("comments_dedupe_policy", None)
    ingestion_params["dedupe_policy"] = [PRIOR_RUN_POLICY]
    ingestion_params["posts_dedupe_policy"] = []
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()

    prior_run = comment_storage.create_new_run_dir("2026_05_29-10:00:00")
    post_storage.append_records(
        [mock_post_row("t3_post_old")],
        prior_run,
    )
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [
                mock_post_row("t3_post_old"),
                mock_post_row("t3_post_new"),
            ],
            [mock_comment_row("t1_comment_new")],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 2,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    seen = post_storage.load_seen_ids_from_disk(run_dir, "reddit_fullname")
    assert seen == {"t3_post_old", "t3_post_new"}
    assert metadata.get("rows_skipped_as_duplicates", 0) == 0
    assert metadata.get("skipped_as_duplicates_by_record_type", {}).get("reddit.post", 0) == 0
    assert "posts_skipped_as_duplicates" not in metadata


def test_resume_skips_completed_subreddits(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_reddit_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_reddit.build_sync_tasks(ingestion_params)
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_reddit.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    metadata["tasks"]["alphasub"]["status"] = "completed"
    metadata["tasks"]["alphasub"]["comments_collected"] = 1
    comment_storage.append_records(
        [mock_comment_row("t1_comment_a1")],
        run_dir,
    )
    metadata["row_count"] = 1
    comment_storage.write_run_metadata_atomic(run_dir, metadata)

    calls: list[str] = []

    def fake_fetch(
        reddit: Any,
        fetch_cfg: dict[str, Any],
        subreddit: str,
        *,
        sync_timestamp: str,
        include_posts: bool,
        include_comments: bool,
    ):
        calls.append(subreddit)
        return (
            [mock_post_row("t3_post_b1")],
            [mock_comment_row("t1_comment_b1")],
            {
                "subreddit": subreddit,
                "listing": "hot",
                "limit_per_subreddit": 2,
                "posts_collected": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    resumed_metadata = comment_storage.load_run_metadata(run_dir)
    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        resumed_metadata,
        sync_tasks,
        include_comments=True,
        include_posts=True,
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
    comment_storage = RedditStorageManager(StorageStage.RAW, VALID_REDDIT_DATASET_ID)
    post_storage = comment_storage.post_storage()
    run_dir = comment_storage.create_new_run_dir("2026_05_30-10:00:00")
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
        include_posts: bool,
        include_comments: bool,
    ):
        return (
            [mock_post_row("t3_post_a1")],
            [mock_comment_row("t1_comment_a1")],
            {
                "subreddit": subreddit,
                "listing": fetch_cfg.get("listing", "hot"),
                "limit_per_subreddit": fetch_cfg["limit_per_task"],
                "posts_collected": 1,
                "comments_collected": 1,
            },
        )

    monkeypatch.setattr(sync_reddit, "fetch_records_for_subreddit", fake_fetch)

    sync_reddit.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        comment_storage,
        post_storage,
        metadata,
        sync_tasks[:1],
        include_comments=True,
        include_posts=True,
    )

    assert comment_storage.records_filename == "comments.parquet"
    assert post_storage.records_filename == "posts.parquet"
    assert (run_dir / "comments.parquet").exists()
    assert (run_dir / "posts.parquet").exists()
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
        expected_posts = "posts.parquet"

        sync_reddit.sync_records(TEST_INGEST_CONFIG_PATH)
        comment_storage = run_tasks.call_args.args[3]
        post_storage = run_tasks.call_args.args[4]
        result_comments = comment_storage.records_filename
        result_posts = post_storage.records_filename

        assert init_client.called is True
        assert result_comments == expected_comments
        assert result_posts == expected_posts


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
            include_posts=True,
            include_comments=False,
        )
        result = captured["limit"]

        assert result == expected
