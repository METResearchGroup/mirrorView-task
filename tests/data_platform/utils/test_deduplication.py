from __future__ import annotations

from unittest.mock import MagicMock

from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    policy_includes_prior_runs,
)

CURRENT_FILE = "data/bluesky/bluesky_00000000-0000-4000-8000-000000000001/raw/2026_05_30-10:00:00/posts.csv"


def test_session_warm_loads_current_run_only_by_default() -> None:
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-a"}
    config = DedupeConfig(id_column="uri", filename="posts.csv")
    session = DedupeSession(config)
    session.warm(storage, CURRENT_FILE)

    assert session.seen_ids == {"uri-a"}
    storage.load_seen_ids_from_disk.assert_called_once_with(CURRENT_FILE, "uri")
    storage.load_seen_ids_from_all_runs.assert_not_called()


def test_session_warm_unions_prior_runs_when_enabled() -> None:
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-a"}
    storage.load_seen_ids_from_all_runs.return_value = {"uri-b"}
    config = DedupeConfig(
        id_column="uri", filename="posts.csv", include_prior_runs=True
    )
    session = DedupeSession(config)
    session.warm(storage, CURRENT_FILE)

    assert session.seen_ids == {"uri-a", "uri-b"}
    storage.load_seen_ids_from_all_runs.assert_called_once_with("uri", "posts.csv")


def test_session_warm_does_not_scan_prior_runs_when_disabled() -> None:
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-b"}
    config = DedupeConfig(id_column="uri", filename="posts.csv")
    session = DedupeSession(config)
    session.seen_ids = {"uri-a"}
    session.warm(storage, CURRENT_FILE)

    assert session.seen_ids == {"uri-a", "uri-b"}
    storage.load_seen_ids_from_all_runs.assert_not_called()


def test_policy_includes_prior_runs() -> None:
    assert policy_includes_prior_runs(["current_run"]) is False
    assert policy_includes_prior_runs(["current_run", "prior_runs_same_dataset"]) is True
    assert policy_includes_prior_runs(["prior_runs_all_datasets"]) is True
    assert policy_includes_prior_runs(None) is False


def test_session_filter_rows_skips_seen() -> None:
    config = DedupeConfig(id_column="uri")
    session = DedupeSession(config)
    session.seen_ids = {"uri-a"}

    kept, skipped = session.filter_rows(
        [
            {"uri": "uri-a", "text": "dup"},
            {"uri": "uri-b", "text": "new"},
        ]
    )

    assert kept == [{"uri": "uri-b", "text": "new"}]
    assert skipped == 1


def test_note_appended_updates_seen_ids() -> None:
    config = DedupeConfig(id_column="uri")
    session = DedupeSession(config)
    session.seen_ids = {"uri-a"}

    session.note_appended([{"uri": "uri-b"}, {"uri": "uri-c"}])

    assert session.seen_ids == {"uri-a", "uri-b", "uri-c"}
