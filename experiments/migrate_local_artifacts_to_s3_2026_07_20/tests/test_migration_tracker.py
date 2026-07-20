"""Unit tests for MigrationTracker."""

from __future__ import annotations

from pathlib import Path

import pytest

from experiments.migrate_local_artifacts_to_s3_2026_07_20.migration_tracker import (
    MigrationStatus,
    MigrationTracker,
)


def _row(
    local_path: str,
    *,
    status: str = "pending",
    prefix: str = "experiments/foo",
    size: int = 10,
    sha: str = "abc",
) -> dict:
    return {
        "local_path": local_path,
        "s3_key": local_path,
        "file_size_bytes": size,
        "sha256": sha,
        "mtime_ns": 1,
        "experiment_prefix": prefix,
        "status": status,
    }


@pytest.fixture
def tracker(tmp_path: Path) -> MigrationTracker:
    db = tmp_path / "t.db"
    t = MigrationTracker(db)
    t.init_schema()
    yield t
    t.close()


def test_schema_create(tracker: MigrationTracker) -> None:
    counts = tracker.summary_counts()
    assert counts == {}


def test_unique_insert_idempotent(tracker: MigrationTracker) -> None:
    r = _row("experiments/foo/a.csv")
    first = tracker.register_files([r])
    second = tracker.register_files([r])
    assert first["inserted"] == 1
    assert second["inserted"] == 0
    assert second["already_present"] == 1


def test_s3_key_collision_raises(tracker: MigrationTracker) -> None:
    tracker.register_files([_row("experiments/foo/a.csv")])
    with pytest.raises(ValueError, match="s3_key collision"):
        tracker.register_files(
            [
                {
                    **_row("experiments/foo/b.csv"),
                    "s3_key": "experiments/foo/a.csv",
                }
            ]
        )


def test_status_transitions(tracker: MigrationTracker) -> None:
    path = "experiments/foo/a.csv"
    tracker.register_files([_row(path)])
    tracker.mark_started(path)
    assert tracker.list_rows(status=MigrationStatus.IN_PROGRESS)[0]["local_path"] == path
    tracker.mark_completed(path)
    assert tracker.list_rows(status=MigrationStatus.COMPLETED)[0]["local_path"] == path
    tracker.mark_verified(path)
    assert tracker.list_rows(status=MigrationStatus.VERIFIED)[0]["local_path"] == path


def test_get_files_to_upload_excludes_failed_completed(tracker: MigrationTracker) -> None:
    tracker.register_files(
        [
            _row("experiments/foo/p.csv"),
            _row("experiments/foo/f.csv"),
            _row("experiments/foo/c.csv"),
        ]
    )
    tracker.mark_started("experiments/foo/f.csv")
    tracker.mark_failed("experiments/foo/f.csv", "boom")
    tracker.mark_started("experiments/foo/c.csv")
    tracker.mark_completed("experiments/foo/c.csv")
    tracker.mark_started("experiments/foo/p.csv")  # leave in_progress

    rows = tracker.get_files_to_upload()
    paths = {r["local_path"] for r in rows}
    assert paths == {"experiments/foo/p.csv"}
    assert "experiments/foo/f.csv" not in paths
    assert "experiments/foo/c.csv" not in paths


def test_reset_failed_to_pending(tracker: MigrationTracker) -> None:
    tracker.register_files([_row("experiments/foo/a.csv")])
    tracker.mark_started("experiments/foo/a.csv")
    tracker.mark_failed("experiments/foo/a.csv", "x")
    n = tracker.reset_failed_to_pending()
    assert n == 1
    assert tracker.get_files_to_upload()[0]["local_path"] == "experiments/foo/a.csv"


def test_prefix_filter(tracker: MigrationTracker) -> None:
    tracker.register_files(
        [
            _row("experiments/a/x.csv", prefix="experiments/a"),
            _row("experiments/b/y.csv", prefix="experiments/b"),
        ]
    )
    rows = tracker.get_files_to_upload(prefix="experiments/a")
    assert len(rows) == 1
    assert rows[0]["local_path"] == "experiments/a/x.csv"
