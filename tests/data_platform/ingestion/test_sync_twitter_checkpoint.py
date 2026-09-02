from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest

from data_platform.ingestion import sync_twitter
from data_platform.ingestion.sync_checkpoint import parse_max_posts
from data_platform.utils.dataset import ValidDataFormats, write_dataset_manifest
from data_platform.utils.deduplication import PRIOR_RUN_POLICY
from data_platform.utils.storage import StorageStage, TwitterStorageManager
from tests.data_platform.constants import TEST_INGEST_CONFIG_PATH, VALID_TWITTER_DATASET_ID
from tests.data_platform.ingestion.twitter_conftest import mock_tweet_row


def _minimal_twitter_sync_config() -> dict[str, Any]:
    return {
        "dataset_id": VALID_TWITTER_DATASET_ID,
        "name": "test",
        "description": "test",
        "date": "2026-05-31",
        "record_types": [sync_twitter.TWEETS_RECORD_TYPE],
        "ingestion_params": {
            "dedupe_policy": ["current_run", PRIOR_RUN_POLICY],
            "keywords": ["alpha", "beta"],
            "limit_per_task": 2,
            "lang": "en",
            "exclude": ["reply", "retweet", "quote"],
        },
    }


def test_init_sync_metadata_task_ledger() -> None:
    config = _minimal_twitter_sync_config()
    sync_tasks = sync_twitter.build_sync_tasks(config["ingestion_params"])
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    assert metadata["sync_status"] == "in_progress"
    assert set(metadata["tasks"]) == {"alpha", "beta"}
    assert metadata["tasks"]["alpha"]["status"] == "pending"
    assert metadata["tasks"]["alpha"]["kind"] == "twitter"


def test_run_sync_tasks_appends_per_keyword(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    rows_by_keyword = {
        "alpha": [mock_tweet_row("1000000000000000001", keyword="alpha")],
        "beta": [mock_tweet_row("1000000000000000002", keyword="beta")],
    }

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        rows = rows_by_keyword[keyword]
        return rows, {
            "pages_fetched": 1,
            "rows_collected": len(rows),
        }

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert metadata["tasks"]["alpha"]["status"] == "completed"
    assert metadata["tasks"]["beta"]["status"] == "completed"
    assert metadata["row_count"] == 2
    assert (run_dir / "posts.csv").exists()
    assert not (run_dir / "posts.parquet").exists()
    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {
        "1000000000000000001",
        "1000000000000000002",
    }


def test_run_sync_tasks_skips_prior_run_tweets_when_enabled(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["dedupe_policy"] = ["current_run", PRIOR_RUN_POLICY]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)

    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    storage.append_records(
        [mock_tweet_row("1000000000000000000", keyword="alpha")],
        run_dir,
    )
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        return (
            [
                mock_tweet_row("1000000000000000000", keyword=keyword),
                mock_tweet_row("1000000000000000001", keyword=keyword),
            ],
            {"pages_fetched": 1, "rows_collected": 2},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {
        "1000000000000000000",
        "1000000000000000001",
    }
    assert metadata["rows_skipped_as_duplicates"] == 1
    assert metadata["skipped_as_duplicates_by_record_type"]["twitter.tweet"] == 1
    assert "tweets_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_does_not_skip_prior_runs_when_disabled(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["dedupe_policy"] = ["current_run"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)

    prior_run = storage.create_new_run_dir("2026_05_29-10:00:00")
    storage.append_records(
        [mock_tweet_row("1000000000000000000", keyword="alpha")],
        prior_run,
    )

    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        return (
            [
                mock_tweet_row("1000000000000000000", keyword=keyword),
                mock_tweet_row("1000000000000000001", keyword=keyword),
            ],
            {"pages_fetched": 1, "rows_collected": 2},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {
        "1000000000000000000",
        "1000000000000000001",
    }
    assert metadata.get("rows_skipped_as_duplicates", 0) == 0
    assert "tweets_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_skips_ids_from_other_dataset(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "twitter_00000000-0000-4000-8000-000000000002"
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    other_storage = TwitterStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [mock_tweet_row("1000000000000000000", keyword="alpha")],
        other_run,
    )

    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        return (
            [
                mock_tweet_row("1000000000000000000", keyword=keyword),
                mock_tweet_row("1000000000000000001", keyword=keyword),
            ],
            {"pages_fetched": 1, "rows_collected": 2},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {
        "1000000000000000000",
        "1000000000000000001",
    }
    assert metadata["rows_skipped_as_duplicates"] == 0
    assert metadata["skipped_as_duplicates_by_record_type"]["twitter.tweet"] == 0
    assert "tweets_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_respects_current_run_only_policy(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "twitter_00000000-0000-4000-8000-000000000002"
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["dedupe_policy"] = ["current_run"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    other_storage = TwitterStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [mock_tweet_row("1000000000000000000", keyword="alpha")],
        other_run,
    )

    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        return (
            [mock_tweet_row("1000000000000000000", keyword=keyword)],
            {"pages_fetched": 1, "rows_collected": 1},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "tweet_id") == {"1000000000000000000"}
    assert metadata.get("rows_skipped_as_duplicates", 0) == 0
    assert "tweets_skipped_as_duplicates" not in metadata


def test_resume_skips_completed_tasks(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    metadata["tasks"]["alpha"]["status"] = "completed"
    metadata["tasks"]["alpha"]["rows_collected"] = 1
    storage.append_records(
        [mock_tweet_row("1000000000000000001", keyword="alpha")],
        run_dir,
    )
    metadata["row_count"] = 1
    storage.write_run_metadata_atomic(run_dir, metadata)

    calls: list[str] = []

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        calls.append(keyword)
        return (
            [mock_tweet_row("1000000000000000002", keyword=keyword)],
            {"pages_fetched": 1, "rows_collected": 1},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    resumed_metadata = storage.load_run_metadata(run_dir)
    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        resumed_metadata,
        sync_tasks,
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert calls == ["beta"]
    assert resumed_metadata["tasks"]["beta"]["status"] == "completed"
    assert resumed_metadata["row_count"] == 2


def test_run_sync_tasks_writes_parquet_when_storage_format_is_parquet(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies the Twitter write loop stores posts.parquet for a parquet dataset."""
    write_dataset_manifest(
        "twitter",
        VALID_TWITTER_DATASET_ID,
        name="test",
        ingestion_config="data_platform/ingestion/configs/twitter/mirrorview.yaml",
        data_format=ValidDataFormats.PARQUET,
    )
    config = _minimal_twitter_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_twitter.build_sync_tasks(ingestion_params)
    storage = TwitterStorageManager(StorageStage.RAW, VALID_TWITTER_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_twitter.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_fetch(
        client: Any,
        keyword: str,
        *,
        limit: int,
        lang: str,
        exclude: list[str],
        sync_timestamp: str,
    ):
        return (
            [mock_tweet_row("1000000000000000001", keyword=keyword)],
            {"pages_fetched": 1, "rows_collected": 1},
        )

    monkeypatch.setattr(sync_twitter, "fetch_posts_for_keyword", fake_fetch)

    sync_twitter.run_sync_tasks(
        MagicMock(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        sync_timestamp="2026_05_30-10:00:00",
        filename=storage.records_filename,
    )

    assert storage.records_filename == "posts.parquet"
    assert (run_dir / "posts.parquet").exists()
    assert not (run_dir / "posts.csv").exists()


class TestSyncRecords:
    """Tests for sync_records."""

    def _patch_load_and_fetch(
        self,
        monkeypatch: pytest.MonkeyPatch,
        config: dict[str, Any],
    ) -> tuple[MagicMock, MagicMock]:
        monkeypatch.setattr(sync_twitter, "load_config", lambda path: config)
        monkeypatch.setattr(
            sync_twitter, "ensure_dataset_manifest", lambda *args, **kwargs: None
        )
        init_client = MagicMock(name="init_twitter_client")
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_twitter, "init_twitter_client", init_client)
        monkeypatch.setattr(sync_twitter, "run_sync_tasks", run_tasks)
        return init_client, run_tasks

    def test_accepts_tweets_record_type(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = _minimal_twitter_sync_config()
        init_client, run_tasks = self._patch_load_and_fetch(monkeypatch, config)

        result = sync_twitter.sync_records(TEST_INGEST_CONFIG_PATH)

        expected_called = True
        assert result is not None
        assert init_client.called is expected_called
        assert run_tasks.called is expected_called

    def test_allows_extra_record_types_when_tweet_present(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = _minimal_twitter_sync_config()
        config["record_types"] = [sync_twitter.TWEETS_RECORD_TYPE, "twitter.user"]
        init_client, run_tasks = self._patch_load_and_fetch(monkeypatch, config)

        result = sync_twitter.sync_records(TEST_INGEST_CONFIG_PATH)

        expected_called = True
        assert result is not None
        assert init_client.called is expected_called
        assert run_tasks.called is expected_called

    @pytest.mark.parametrize(
        "record_types",
        [
            [],
            ["twitter.user"],
            "twitter.tweet",
            None,
        ],
    )
    def test_rejects_empty_or_wrong_record_types(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
        record_types: Any,
    ) -> None:
        config = _minimal_twitter_sync_config()
        config["record_types"] = record_types
        init_client, run_tasks = self._patch_load_and_fetch(monkeypatch, config)

        with pytest.raises(
            ValueError, match="Unsupported record types for checkpoint sync"
        ):
            sync_twitter.sync_records(TEST_INGEST_CONFIG_PATH)

        init_client.assert_not_called()
        run_tasks.assert_not_called()

    def test_rejects_missing_record_types(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config = _minimal_twitter_sync_config()
        del config["record_types"]
        init_client, run_tasks = self._patch_load_and_fetch(monkeypatch, config)

        with pytest.raises(KeyError):
            sync_twitter.sync_records(TEST_INGEST_CONFIG_PATH)

        init_client.assert_not_called()
        run_tasks.assert_not_called()

    def test_passes_parquet_filename_when_output_format_is_parquet(
        self,
        data_root,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verifies sync_records passes posts.parquet after writing a parquet manifest."""
        config = _minimal_twitter_sync_config()
        config["output_format"] = "parquet"
        monkeypatch.setattr(sync_twitter, "load_config", lambda path: config)
        init_client = MagicMock(name="init_twitter_client")
        run_tasks = MagicMock(name="run_sync_tasks")
        monkeypatch.setattr(sync_twitter, "init_twitter_client", init_client)
        monkeypatch.setattr(sync_twitter, "run_sync_tasks", run_tasks)
        expected = "posts.parquet"

        sync_twitter.sync_records(TEST_INGEST_CONFIG_PATH)
        result = run_tasks.call_args.kwargs["filename"]

        assert init_client.called is True
        assert result == expected


class TestBuildSyncTasks:
    """Tests for build_sync_tasks()."""

    def test_builds_one_task_per_keywords_entry(self) -> None:
        ingestion_params = {"keywords": ["alpha", "beta"]}
        expected = [
            sync_twitter.TwitterTask(task_id="alpha", keyword="alpha"),
            sync_twitter.TwitterTask(task_id="beta", keyword="beta"),
        ]

        result = sync_twitter.build_sync_tasks(ingestion_params)

        assert result == expected

    def test_strips_keywords_entries_and_does_not_quote(self) -> None:
        ingestion_params = {"keywords": [" gun control "]}
        expected = [
            sync_twitter.TwitterTask(task_id="gun control", keyword="gun control"),
        ]

        result = sync_twitter.build_sync_tasks(ingestion_params)

        assert result == expected

    def test_rejects_blank_keywords_entries(self) -> None:
        ingestion_params = {"keywords": ["alpha", ""]}

        with pytest.raises(ValueError, match="non-empty strings"):
            sync_twitter.build_sync_tasks(ingestion_params)

    @pytest.mark.parametrize(
        "ingestion_params",
        [
            {},
            {"keywords": []},
            {"keywords": "example"},
            {"keywords": None},
        ],
    )
    def test_rejects_missing_or_invalid_search_terms(
        self,
        ingestion_params: dict[str, Any],
    ) -> None:
        with pytest.raises(ValueError, match="keywords"):
            sync_twitter.build_sync_tasks(ingestion_params)


class TestEffectiveLimitPerKeyword:
    """Tests for _effective_limit_per_keyword()."""

    def test_uses_limit_per_task(self) -> None:
        ingestion_params = {"limit_per_task": 8}
        expected = 8

        result = sync_twitter._effective_limit_per_keyword(ingestion_params, None)

        assert result == expected

    def test_raises_key_error_when_limit_per_task_is_missing(self) -> None:
        ingestion_params: dict[str, Any] = {}

        with pytest.raises(KeyError):
            sync_twitter._effective_limit_per_keyword(ingestion_params, None)

    def test_clamps_limit_per_task_to_remaining_rows(self) -> None:
        ingestion_params = {"limit_per_task": 10}
        expected = 3

        result = sync_twitter._effective_limit_per_keyword(ingestion_params, 3)

        assert result == expected


class TestRemainingPostBudget:
    """Tests for parse_max_posts() with Twitter remaining post budget."""

    def test_remaining_budget_uses_max_posts(self) -> None:
        ingestion_params = {"max_posts": 8}
        metadata = {"row_count": 3}
        expected = 5

        cap = parse_max_posts(ingestion_params)
        result = sync_twitter._remaining_post_budget(metadata, cap)

        assert result == expected

    def test_effective_limit_uses_max_posts_remaining(self) -> None:
        ingestion_params = {"max_posts": 8, "limit_per_task": 8}
        metadata = {"row_count": 0}
        expected = 8

        cap = parse_max_posts(ingestion_params)
        remaining = sync_twitter._remaining_post_budget(metadata, cap)
        result = sync_twitter._effective_limit_per_keyword(ingestion_params, remaining)

        assert result == expected
