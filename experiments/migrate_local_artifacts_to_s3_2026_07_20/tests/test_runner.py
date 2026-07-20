"""Unit tests for runner (mocked subprocess)."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from experiments.migrate_local_artifacts_to_s3_2026_07_20.migration_tracker import (
    MigrationStatus,
    MigrationTracker,
)
from experiments.migrate_local_artifacts_to_s3_2026_07_20.runner import main


def _seed_db(db: Path, repo_root: Path, rel: str, content: bytes = b"hello\n") -> None:
    abs_path = repo_root / rel
    abs_path.parent.mkdir(parents=True, exist_ok=True)
    abs_path.write_bytes(content)
    tracker = MigrationTracker(db)
    tracker.init_schema()
    tracker.register_files(
        [
            {
                "local_path": rel,
                "s3_key": rel,
                "file_size_bytes": len(content),
                "sha256": "deadbeef",
                "mtime_ns": 1,
                "experiment_prefix": "experiments/demo_exp",
                "status": MigrationStatus.PENDING,
            }
        ]
    )
    tracker.close()


def test_upload_started_completed(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    repo = tmp_path / "repo"
    rel = "experiments/demo_exp/a.csv"
    _seed_db(db, repo, rel)
    script = tmp_path / "upload_to_s3.sh"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)

    with patch(
        "experiments.migrate_local_artifacts_to_s3_2026_07_20.runner.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        rc = main(
            [
                "upload",
                "--db",
                str(db),
                "--repo-root",
                str(repo),
                "--upload-script",
                str(script),
            ]
        )
    assert rc == 0
    tracker = MigrationTracker(db)
    try:
        rows = tracker.list_rows()
        assert rows[0]["status"] == MigrationStatus.COMPLETED
    finally:
        tracker.close()


def test_upload_started_failed_nonzero(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    repo = tmp_path / "repo"
    rel = "experiments/demo_exp/a.csv"
    _seed_db(db, repo, rel)
    script = tmp_path / "upload_to_s3.sh"
    script.write_text("#!/bin/sh\nexit 1\n", encoding="utf-8")
    script.chmod(0o755)

    with patch(
        "experiments.migrate_local_artifacts_to_s3_2026_07_20.runner.subprocess.run"
    ) as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="aws boom")
        rc = main(
            [
                "upload",
                "--db",
                str(db),
                "--repo-root",
                str(repo),
                "--upload-script",
                str(script),
            ]
        )
    assert rc == 1
    tracker = MigrationTracker(db)
    try:
        row = tracker.list_rows()[0]
        assert row["status"] == MigrationStatus.FAILED
        assert "aws boom" in (row["error_message"] or "")
    finally:
        tracker.close()


def test_dry_run_does_not_mutate_db(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    repo = tmp_path / "repo"
    rel = "experiments/demo_exp/a.csv"
    _seed_db(db, repo, rel)
    script = tmp_path / "upload_to_s3.sh"
    script.write_text("#!/bin/sh\necho DRY-RUN: ok\n", encoding="utf-8")
    script.chmod(0o755)

    with patch(
        "experiments.migrate_local_artifacts_to_s3_2026_07_20.runner.subprocess.run",
        wraps=subprocess.run,
    ):
        rc = main(
            [
                "upload",
                "--dry-run",
                "--db",
                str(db),
                "--repo-root",
                str(repo),
                "--upload-script",
                str(script),
            ]
        )
    assert rc == 0
    tracker = MigrationTracker(db)
    try:
        assert tracker.list_rows()[0]["status"] == MigrationStatus.PENDING
    finally:
        tracker.close()


def test_preflight_missing_file_marks_failed(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    repo = tmp_path / "repo"
    rel = "experiments/demo_exp/missing.csv"
    tracker = MigrationTracker(db)
    tracker.init_schema()
    tracker.register_files(
        [
            {
                "local_path": rel,
                "s3_key": rel,
                "file_size_bytes": 5,
                "sha256": "x",
                "mtime_ns": 1,
                "experiment_prefix": "experiments/demo_exp",
                "status": MigrationStatus.PENDING,
            }
        ]
    )
    tracker.close()

    script = tmp_path / "upload_to_s3.sh"
    script.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    script.chmod(0o755)

    with patch(
        "experiments.migrate_local_artifacts_to_s3_2026_07_20.runner.subprocess.run"
    ) as mock_run:
        rc = main(
            [
                "upload",
                "--db",
                str(db),
                "--repo-root",
                str(repo),
                "--upload-script",
                str(script),
            ]
        )
        mock_run.assert_not_called()
    assert rc == 1
    tracker = MigrationTracker(db)
    try:
        row = tracker.list_rows()[0]
        assert row["status"] == MigrationStatus.FAILED
        assert "missing" in (row["error_message"] or "").lower()
    finally:
        tracker.close()
