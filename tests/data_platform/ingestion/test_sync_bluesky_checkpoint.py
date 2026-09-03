from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner

from data_platform.ingestion import sync_bluesky
from data_platform.ingestion.integrations.bluesky import BlueskyClient
from data_platform.ingestion.sync_checkpoint import (
    SyncStatus,
    flush_run_metadata,
    validate_tasks_for_resume,
)
from data_platform.utils.storage import BlueskyStorageManager, StorageStage
from tests.data_platform.conftest import make_ingestion_row
from tests.data_platform.constants import TEST_INGEST_CONFIG_PATH, VALID_DATASET_ID
from tests.data_platform.ingestion.conftest import (
    minimal_sync_config,
    mock_post,
    mock_search_response,
)


def make_bluesky_client() -> BlueskyClient:
    """Return a BlueskyClient with a no-op internal atproto Client."""
    return BlueskyClient(client=MagicMock())


def test_build_sync_tasks_requires_keywords_list() -> None:
    with pytest.raises(ValueError, match="keywords"):
        sync_bluesky.build_sync_tasks({})
    with pytest.raises(ValueError, match="non-empty strings"):
        sync_bluesky.build_sync_tasks({"keywords": ["alpha", ""]})


def test_build_sync_tasks_quotes_keywords_with_spaces() -> None:
    tasks = sync_bluesky.build_sync_tasks({"keywords": ["gun control"]})
    assert len(tasks) == 1
    assert tasks[0].task_id == "gun control"
    assert tasks[0].query == '"gun control"'


def test_init_sync_metadata_task_ledger() -> None:
    config = minimal_sync_config()
    sync_tasks = sync_bluesky.build_sync_tasks(config["ingestion_params"])
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    assert metadata["sync_status"] == "in_progress"
    assert set(metadata["tasks"]) == {"alpha", "beta"}
    assert metadata["tasks"]["alpha"]["status"] == "pending"
    assert metadata["tasks"]["alpha"]["kind"] == "bluesky"


def test_run_sync_tasks_appends_per_keyword(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    posts_by_query = {
        "alpha": [mock_post("at://did:plc:ex/app.bsky.feed.post/a1")],
        "beta": [mock_post("at://did:plc:ex/app.bsky.feed.post/b1")],
    }

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response(posts_by_query[query])

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
        filename=storage.records_filename,
    )

    assert metadata["tasks"]["alpha"]["status"] == "completed"
    assert metadata["tasks"]["beta"]["status"] == "completed"
    assert metadata["row_count"] == 2
    assert len(storage.load_seen_ids_from_disk(run_dir, "uri")) == 2


def test_run_sync_tasks_skips_ids_from_other_dataset(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "bluesky_00000000-0000-4000-8000-000000000002"
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    other_storage = BlueskyStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [
            make_ingestion_row(
                uri="at://did:plc:ex/app.bsky.feed.post/old",
                url="https://bsky.app/profile/user/post/old",
                author_handle="user",
                text="old",
            )
        ],
        other_run,
    )

    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response(
            [
                mock_post("at://did:plc:ex/app.bsky.feed.post/old"),
                mock_post("at://did:plc:ex/app.bsky.feed.post/new"),
            ]
        )

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "uri") == {
        "at://did:plc:ex/app.bsky.feed.post/old",
        "at://did:plc:ex/app.bsky.feed.post/new",
    }
    assert metadata["rows_skipped_as_duplicates"] == 0
    assert metadata["skipped_as_duplicates_by_record_type"]["app.bsky.feed.post"] == 0
    assert "posts_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_respects_current_run_only_policy(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    other_dataset_id = "bluesky_00000000-0000-4000-8000-000000000002"
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    ingestion_params["dedupe_policy"] = ["current_run"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    other_storage = BlueskyStorageManager(StorageStage.RAW, other_dataset_id)
    other_run = other_storage.create_new_run_dir("2026_05_29-10:00:00")
    other_storage.append_records(
        [
            make_ingestion_row(
                uri="at://did:plc:ex/app.bsky.feed.post/old",
                url="https://bsky.app/profile/user/post/old",
                author_handle="user",
                text="old",
            )
        ],
        other_run,
    )

    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response([mock_post("at://did:plc:ex/app.bsky.feed.post/old")])

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks[:1],
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "uri") == {"at://did:plc:ex/app.bsky.feed.post/old"}
    assert metadata.get("rows_skipped_as_duplicates", 0) == 0
    assert "posts_skipped_as_duplicates" not in metadata


def test_run_sync_tasks_dedupes_within_run(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    duplicate_uri = "at://did:plc:ex/app.bsky.feed.post/dup"

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response([mock_post(duplicate_uri)])

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "uri") == {duplicate_uri}
    assert metadata["row_count"] == 1


def test_resume_skips_completed_tasks(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )
    metadata["tasks"]["alpha"]["status"] = "completed"
    metadata["tasks"]["alpha"]["rows_collected"] = 1
    storage.append_records(
        [
            make_ingestion_row(
                uri="at://did:plc:ex/app.bsky.feed.post/a1",
                url="https://bsky.app/profile/user/post/a1",
                author_handle="user",
                text="x",
            )
        ],
        run_dir,
    )
    metadata["row_count"] = 1
    storage.write_run_metadata_atomic(run_dir, metadata)

    calls: list[str] = []

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        calls.append(query)
        return mock_search_response([mock_post("at://did:plc:ex/app.bsky.feed.post/b1")])

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    resumed_metadata = storage.load_run_metadata(run_dir)
    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        resumed_metadata,
        sync_tasks,
        filename=storage.records_filename,
    )

    assert calls == ["beta"]
    assert resumed_metadata["tasks"]["beta"]["status"] == "completed"
    assert resumed_metadata["row_count"] == 2


def test_resume_dedupes_against_records_from_completed_tasks(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_sync_config()
    ingestion_params = config["ingestion_params"]
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    already_seen_uri = "at://did:plc:ex/app.bsky.feed.post/a1"
    metadata["tasks"]["alpha"]["status"] = "completed"
    metadata["tasks"]["alpha"]["rows_collected"] = 1
    storage.append_records(
        [
            make_ingestion_row(
                uri=already_seen_uri,
                url="https://bsky.app/profile/user/post/a1",
                author_handle="user",
                text="x",
            )
        ],
        run_dir,
    )
    metadata["row_count"] = 1
    storage.write_run_metadata_atomic(run_dir, metadata)

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response(
            [
                mock_post(already_seen_uri),
                mock_post("at://did:plc:ex/app.bsky.feed.post/b1"),
            ]
        )

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    resumed_metadata = storage.load_run_metadata(run_dir)
    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        resumed_metadata,
        sync_tasks,
        filename=storage.records_filename,
    )

    assert storage.load_seen_ids_from_disk(run_dir, "uri") == {
        already_seen_uri,
        "at://did:plc:ex/app.bsky.feed.post/b1",
    }
    assert resumed_metadata["rows_skipped_as_duplicates"] == 1
    assert resumed_metadata["skipped_as_duplicates_by_record_type"]["app.bsky.feed.post"] == 1
    assert "posts_skipped_as_duplicates" not in resumed_metadata
    assert resumed_metadata["row_count"] == 2


def test_resume_keywords_metadata_without_tasks_raises_key_error() -> None:
    config = minimal_sync_config()
    sync_tasks = sync_bluesky.build_sync_tasks(config["ingestion_params"])
    old_metadata = {
        "sync_status": "in_progress",
        "keywords": {"alpha": {"status": "pending"}},
    }
    with pytest.raises(KeyError):
        validate_tasks_for_resume(sync_tasks, old_metadata, entity_label="keywords")


def test_run_sync_tasks_caps_fetch_by_remaining_max_posts(
    data_root,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = minimal_sync_config()
    ingestion_params = dict(config["ingestion_params"])
    ingestion_params["max_posts"] = 2
    ingestion_params["limit_per_task"] = 5
    sync_tasks = sync_bluesky.build_sync_tasks(ingestion_params)
    storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
    run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
    metadata = sync_bluesky.init_sync_metadata(
        config,
        TEST_INGEST_CONFIG_PATH,
        "2026_05_30-10:00:00",
        sync_tasks,
    )

    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response(
            [
                mock_post(f"at://did:plc:ex/app.bsky.feed.post/{query}-1"),
                mock_post(f"at://did:plc:ex/app.bsky.feed.post/{query}-2"),
                mock_post(f"at://did:plc:ex/app.bsky.feed.post/{query}-3"),
            ]
        )

    monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

    sync_bluesky.run_sync_tasks(
        make_bluesky_client(),
        ingestion_params,
        run_dir,
        storage,
        metadata,
        sync_tasks,
        filename=storage.records_filename,
    )

    assert metadata["row_count"] == 2
    assert metadata["tasks"]["alpha"]["status"] == "completed"
    assert metadata["tasks"]["beta"]["status"] == "skipped"


class TestResolveSearchAuthor:
    """Tests for BlueskyClient._resolve_search_author."""

    def test_returns_author_filter(self) -> None:
        ingestion_params = {"author_filter": "alice.bsky.social"}
        expected = "alice.bsky.social"

        result = BlueskyClient._resolve_search_author(ingestion_params)

        assert result == expected

    @pytest.mark.parametrize(
        "ingestion_params",
        [
            {},
            {"author_filter": ""},
            {"author_filter": None},
        ],
    )
    def test_returns_none_when_keys_are_missing_or_empty(
        self,
        ingestion_params: dict[str, Any],
    ) -> None:
        result = BlueskyClient._resolve_search_author(ingestion_params)

        expected = None
        assert result == expected


class TestSearchPostsPage:
    """Tests for BlueskyClient._search_posts_page."""

    def _client_with_empty_search(self) -> BlueskyClient:
        client = make_bluesky_client()
        client._client.app.bsky.feed.search_posts.return_value = mock_search_response([])
        return client

    def test_passes_author_filter_as_search_author(self) -> None:
        client = self._client_with_empty_search()
        ingestion_params = {"sort": "latest", "author_filter": "alice.bsky.social"}
        expected_author = "alice.bsky.social"

        client._search_posts_page(
            ingestion_params, "alpha", page_limit=10
        )

        params = client._client.app.bsky.feed.search_posts.call_args.kwargs["params"]
        result = params.get("author")
        assert result == expected_author
        assert params["q"] == "alpha"
        assert params["limit"] == 10

    def test_omits_author_when_filter_is_absent(self) -> None:
        client = self._client_with_empty_search()
        ingestion_params = {"sort": "latest"}

        client._search_posts_page(
            ingestion_params, "alpha", page_limit=10
        )

        params = client._client.app.bsky.feed.search_posts.call_args.kwargs["params"]
        result = "author" in params
        expected = False
        assert result == expected


class TestFetchPostsForKeywordLimitPerTask:
    """Tests that BlueskyClient.fetch_posts_for_keyword reads limit_per_task."""

    def test_uses_limit_per_task(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        ingestion_params = {"limit_per_task": 1, "sort": "latest"}
        expected = 1

        def fake_search(
            _self: Any,
            _fetch_cfg: dict[str, Any],
            query: str,
            *,
            page_limit: int,
            cursor: str | None = None,
        ):
            return mock_search_response(
                [
                    mock_post("at://did:plc:ex/app.bsky.feed.post/a1"),
                    mock_post("at://did:plc:ex/app.bsky.feed.post/a2"),
                ]
            )

        monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

        result = make_bluesky_client().fetch_posts_for_keyword(
            ingestion_params,
            "alpha",
            task_id="alpha",
            sync_timestamp="2026_05_30-10:00:00",
        )

        assert len(result.rows) == expected


PATCHED_SYNC_TIMESTAMP = "2026_05_30-11:00:00"


@pytest.fixture
def patched_config(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch load_yaml_config so TEST_INGEST_CONFIG_PATH resolves to minimal config."""
    monkeypatch.setattr(
        sync_bluesky,
        "load_yaml_config",
        lambda path: minimal_sync_config(),
    )


@pytest.fixture
def bluesky_client(monkeypatch: pytest.MonkeyPatch) -> None:
    """Patch BlueskyClient to a no-op MagicMock-backed client."""
    monkeypatch.setattr(sync_bluesky, "BlueskyClient", lambda: make_bluesky_client())


def _posts_by_query_search(posts_by_query: dict[str, list[Any]]):
    def fake_search(
        _self: Any,
        _fetch_cfg: dict[str, Any],
        query: str,
        *,
        page_limit: int,
        cursor: str | None = None,
    ):
        return mock_search_response(posts_by_query[query])

    return fake_search


class TestSyncRecordsNewRun:
    """Tests for sync_records_new_run()."""

    def test_creates_run_and_completes_keyword_tasks(
        self,
        data_root,
        patched_config,
        bluesky_client,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "data_platform.ingestion.sync_checkpoint.get_current_timestamp",
            lambda: PATCHED_SYNC_TIMESTAMP,
        )
        monkeypatch.setattr(
            BlueskyClient,
            "_search_posts_page",
            _posts_by_query_search(
                {
                    "alpha": [mock_post("at://did:plc:ex/app.bsky.feed.post/a1")],
                    "beta": [mock_post("at://did:plc:ex/app.bsky.feed.post/b1")],
                }
            ),
        )

        result = sync_bluesky.sync_records_new_run(TEST_INGEST_CONFIG_PATH)

        expected = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID).root_dir / (
            PATCHED_SYNC_TIMESTAMP
        )
        assert result == expected
        metadata = BlueskyStorageManager(
            StorageStage.RAW, VALID_DATASET_ID
        ).load_run_metadata(result)
        assert metadata["tasks"]["alpha"]["status"] == "completed"
        assert metadata["tasks"]["beta"]["status"] == "completed"

    def test_raises_when_unfinished_run_exists(
        self,
        data_root,
        patched_config,
        bluesky_client,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        existing = storage.create_new_run_dir("2026_05_30-10:00:00")
        flush_run_metadata(
            storage,
            existing,
            {"sync_status": SyncStatus.IN_PROGRESS.value, "tasks": {}},
        )

        with pytest.raises(ValueError, match="unfinished"):
            sync_bluesky.sync_records_new_run(TEST_INGEST_CONFIG_PATH)


class TestSyncRecordsFromCheckpoint:
    """Tests for sync_records_from_checkpoint()."""

    def _seed_in_progress_run(self) -> tuple[BlueskyStorageManager, Any]:
        config = minimal_sync_config()
        sync_tasks = sync_bluesky.build_sync_tasks(config["ingestion_params"])
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)
        run_dir = storage.create_new_run_dir("2026_05_30-10:00:00")
        metadata = sync_bluesky.init_sync_metadata(
            config,
            TEST_INGEST_CONFIG_PATH,
            "2026_05_30-10:00:00",
            sync_tasks,
        )
        metadata["tasks"]["alpha"]["status"] = "completed"
        metadata["tasks"]["alpha"]["rows_collected"] = 1
        storage.append_records(
            [
                make_ingestion_row(
                    uri="at://did:plc:ex/app.bsky.feed.post/a1",
                    url="https://bsky.app/profile/user/post/a1",
                    author_handle="user",
                    text="x",
                )
            ],
            run_dir,
        )
        metadata["row_count"] = 1
        storage.write_run_metadata_atomic(run_dir, metadata)
        return storage, run_dir

    def test_resumes_named_unfinished_run(
        self,
        data_root,
        patched_config,
        bluesky_client,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage, run_dir = self._seed_in_progress_run()
        calls: list[str] = []

        def fake_search(
            _self: Any,
            _fetch_cfg: dict[str, Any],
            query: str,
            *,
            page_limit: int,
            cursor: str | None = None,
        ):
            calls.append(query)
            return mock_search_response(
                [mock_post("at://did:plc:ex/app.bsky.feed.post/b1")]
            )

        monkeypatch.setattr(BlueskyClient, "_search_posts_page", fake_search)

        result = sync_bluesky.sync_records_from_checkpoint(
            TEST_INGEST_CONFIG_PATH,
            "2026_05_30-10:00:00",
        )

        assert result == run_dir
        assert calls == ["beta"]
        metadata = storage.load_run_metadata(run_dir)
        assert metadata["tasks"]["beta"]["status"] == "completed"

    def test_resumes_latest_unfinished_run(
        self,
        data_root,
        patched_config,
        bluesky_client,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        storage, run_dir = self._seed_in_progress_run()
        monkeypatch.setattr(
            BlueskyClient,
            "_search_posts_page",
            _posts_by_query_search(
                {
                    "beta": [mock_post("at://did:plc:ex/app.bsky.feed.post/b1")],
                }
            ),
        )

        resolved = sync_bluesky._resolve_resume_run_dir(
            storage, None, True
        )
        result = sync_bluesky.sync_records_from_checkpoint(
            TEST_INGEST_CONFIG_PATH, resolved
        )

        assert result == run_dir
        metadata = storage.load_run_metadata(run_dir)
        assert metadata["tasks"]["beta"]["status"] == "completed"

    def test_latest_raises_when_no_unfinished_run(
        self,
        data_root,
        patched_config,
        bluesky_client,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)

        with pytest.raises(FileNotFoundError):
            sync_bluesky._resolve_resume_run_dir(storage, None, True)

    def test_raises_when_named_run_is_completed(
        self,
        data_root,
        patched_config,
        bluesky_client,
    ) -> None:
        storage, run_dir = self._seed_in_progress_run()
        metadata = storage.load_run_metadata(run_dir)
        metadata["sync_status"] = SyncStatus.COMPLETED.value
        metadata["tasks"]["beta"]["status"] = "completed"
        storage.write_run_metadata_atomic(run_dir, metadata)

        with pytest.raises(ValueError, match="completed"):
            sync_bluesky.sync_records_from_checkpoint(
                TEST_INGEST_CONFIG_PATH,
                "2026_05_30-10:00:00",
            )

    @pytest.mark.parametrize(
        "run_dir, latest",
        [
            ("2026_05_30-10:00:00", True),
            (None, False),
        ],
    )
    def test_resume_requires_run_dir_or_latest(
        self,
        data_root,
        run_dir: str | None,
        latest: bool,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)

        with pytest.raises(ValueError, match="exactly one"):
            sync_bluesky._resolve_resume_run_dir(storage, run_dir, latest)


class TestBlueskySyncCli:
    """Tests for the Bluesky ingest Typer app."""

    def test_help_lists_new_run_and_resume(self) -> None:
        result = CliRunner().invoke(sync_bluesky.app, ["--help"])

        assert result.exit_code == 0
        assert "new-run" in result.stdout
        assert "resume" in result.stdout

    def test_resume_without_run_dir_or_latest_exits_with_error(
        self,
    ) -> None:
        storage = BlueskyStorageManager(StorageStage.RAW, VALID_DATASET_ID)

        with pytest.raises(ValueError, match="exactly one"):
            sync_bluesky._resolve_resume_run_dir(storage, None, False)
