from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock
import warnings

import pytest

from data_platform.utils.deduplication import (
    DedupeConfig,
    DedupeSession,
    PRIOR_RUN_POLICY,
    policy_includes_prior_runs,
)


def test_session_warm_loads_current_run_only_by_default() -> None:
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-a"}
    config = DedupeConfig(id_column="uri", filename="posts.csv")
    session = DedupeSession(config)
    session.warm(storage, Path("/tmp/run"))

    assert session.seen_ids == {"uri-a"}
    storage.load_seen_ids_from_disk.assert_called_once_with(
        Path("/tmp/run"), "uri", filename="posts.csv"
    )
    storage.load_seen_ids_from_all_runs.assert_not_called()


def test_session_warm_unions_prior_runs_when_enabled() -> None:
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-a"}
    storage.load_seen_ids_from_all_runs.return_value = {"uri-b"}
    config = DedupeConfig(
        id_column="uri", filename="posts.csv", include_prior_runs=True
    )
    session = DedupeSession(config)
    session.warm(storage, Path("/tmp/run"))

    assert session.seen_ids == {"uri-a", "uri-b"}
    storage.load_seen_ids_from_all_runs.assert_called_once_with(
        "uri", filename="posts.csv"
    )
    storage = MagicMock()
    storage.load_seen_ids_from_disk.return_value = {"uri-b"}
    config = DedupeConfig(id_column="uri", filename="posts.csv")
    session = DedupeSession(config)
    session.seen_ids = {"uri-a"}
    session.warm(storage, Path("/tmp/run"))

    assert session.seen_ids == {"uri-a", "uri-b"}
    storage.load_seen_ids_from_all_runs.assert_not_called()


class TestPolicyIncludesPriorRuns:
    """Tests for policy_includes_prior_runs()."""

    def test_current_run_only_does_not_include_prior_runs(self) -> None:
        result = policy_includes_prior_runs(["current_run"])
        expected = False
        assert result is expected

    def test_canonical_token_includes_prior_runs_without_warning(self) -> None:
        with warnings.catch_warnings():
            warnings.simplefilter("error", UserWarning)
            result = policy_includes_prior_runs(["current_run", PRIOR_RUN_POLICY])
        expected = True
        assert result is expected

    def test_legacy_alias_includes_prior_runs_and_warns(self) -> None:
        with pytest.warns(UserWarning, match="prior_runs_all_datasets"):
            result = policy_includes_prior_runs(["prior_runs_all_datasets"])
        expected = True
        assert result is expected

    def test_non_list_policy_does_not_include_prior_runs(self) -> None:
        result = policy_includes_prior_runs(None)
        expected = False
        assert result is expected


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
