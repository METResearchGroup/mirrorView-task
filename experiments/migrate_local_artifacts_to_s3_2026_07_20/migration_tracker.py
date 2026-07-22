"""SQLite tracking API for experiment artifact S3 migration."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from enum import StrEnum
from pathlib import Path
from typing import Any


class MigrationStatus(StrEnum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    VERIFIED = "verified"


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS migration_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  local_path TEXT NOT NULL UNIQUE,
  s3_key TEXT NOT NULL,
  file_size_bytes INTEGER NOT NULL,
  sha256 TEXT,
  mtime_ns INTEGER,
  experiment_prefix TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending'
    CHECK(status IN (
      'pending','in_progress','completed','failed','skipped','verified'
    )),
  started_at TEXT,
  completed_at TEXT,
  verified_at TEXT,
  error_message TEXT,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now')),
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%SZ', 'now'))
);

CREATE INDEX IF NOT EXISTS idx_migration_status
  ON migration_files(status);
CREATE INDEX IF NOT EXISTS idx_migration_prefix
  ON migration_files(experiment_prefix);
CREATE INDEX IF NOT EXISTS idx_migration_status_prefix
  ON migration_files(status, experiment_prefix);
CREATE UNIQUE INDEX IF NOT EXISTS idx_migration_s3_key
  ON migration_files(s3_key);
"""


class MigrationTracker:
    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row

    def init_schema(self) -> None:
        """Create tables/indexes if missing."""
        self._conn.executescript(_SCHEMA_SQL)
        self._conn.commit()

    def register_files(
        self,
        rows: list[dict[str, Any]],
        *,
        refresh_metadata: bool = False,
    ) -> dict[str, int]:
        inserted = 0
        already_present = 0
        refreshed = 0
        skipped_empty = 0

        for row in rows:
            local_path = row["local_path"]
            s3_key = row["s3_key"]
            status = row["status"]
            if status == MigrationStatus.SKIPPED:
                skipped_empty += 1

            existing_by_key = self._conn.execute(
                "SELECT local_path FROM migration_files WHERE s3_key = ?",
                (s3_key,),
            ).fetchone()
            if existing_by_key is not None and existing_by_key["local_path"] != local_path:
                raise ValueError(
                    f"s3_key collision: {s3_key!r} already registered for "
                    f"{existing_by_key['local_path']!r}, also claimed by {local_path!r}"
                )

            existing = self._conn.execute(
                "SELECT status FROM migration_files WHERE local_path = ?",
                (local_path,),
            ).fetchone()

            if existing is None:
                self._conn.execute(
                    """
                    INSERT INTO migration_files (
                      local_path, s3_key, file_size_bytes, sha256, mtime_ns,
                      experiment_prefix, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        local_path,
                        s3_key,
                        int(row["file_size_bytes"]),
                        row.get("sha256"),
                        row.get("mtime_ns"),
                        row["experiment_prefix"],
                        status,
                    ),
                )
                inserted += 1
                continue

            already_present += 1
            if not refresh_metadata:
                continue
            if existing["status"] in (
                MigrationStatus.COMPLETED,
                MigrationStatus.VERIFIED,
            ):
                continue
            self._conn.execute(
                """
                UPDATE migration_files
                SET file_size_bytes = ?,
                    sha256 = ?,
                    mtime_ns = ?,
                    status = ?,
                    updated_at = ?
                WHERE local_path = ?
                """,
                (
                    int(row["file_size_bytes"]),
                    row.get("sha256"),
                    row.get("mtime_ns"),
                    status,
                    _utc_now(),
                    local_path,
                ),
            )
            refreshed += 1

        self._conn.commit()
        return {
            "inserted": inserted,
            "already_present": already_present,
            "refreshed": refreshed,
            "skipped_empty": skipped_empty,
        }

    def mark_started(self, local_path: str) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE migration_files
            SET status = ?,
                started_at = ?,
                error_message = NULL,
                updated_at = ?
            WHERE local_path = ?
            """,
            (MigrationStatus.IN_PROGRESS, now, now, local_path),
        )
        self._conn.commit()

    def mark_completed(self, local_path: str) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE migration_files
            SET status = ?,
                completed_at = ?,
                error_message = NULL,
                updated_at = ?
            WHERE local_path = ?
            """,
            (MigrationStatus.COMPLETED, now, now, local_path),
        )
        self._conn.commit()

    def mark_failed(self, local_path: str, error_message: str) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE migration_files
            SET status = ?,
                completed_at = ?,
                error_message = ?,
                updated_at = ?
            WHERE local_path = ?
            """,
            (MigrationStatus.FAILED, now, error_message, now, local_path),
        )
        self._conn.commit()

    def mark_verified(self, local_path: str) -> None:
        now = _utc_now()
        self._conn.execute(
            """
            UPDATE migration_files
            SET status = ?,
                verified_at = ?,
                error_message = NULL,
                updated_at = ?
            WHERE local_path = ?
            """,
            (MigrationStatus.VERIFIED, now, now, local_path),
        )
        self._conn.commit()

    def get_files_to_upload(
        self,
        *,
        prefix: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        sql = """
            SELECT *
            FROM migration_files
            WHERE status IN ('pending', 'in_progress')
        """
        params: list[Any] = []
        if prefix is not None:
            sql += " AND experiment_prefix = ?"
            params.append(prefix)
        sql += " ORDER BY local_path"
        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))
        rows = self._conn.execute(sql, params).fetchall()
        return [dict(r) for r in rows]

    def reset_failed_to_pending(self, *, prefix: str | None = None) -> int:
        now = _utc_now()
        sql = """
            UPDATE migration_files
            SET status = 'pending',
                error_message = NULL,
                started_at = NULL,
                completed_at = NULL,
                updated_at = ?
            WHERE status = 'failed'
        """
        params: list[Any] = [now]
        if prefix is not None:
            sql += " AND experiment_prefix = ?"
            params.append(prefix)
        cur = self._conn.execute(sql, params)
        self._conn.commit()
        return int(cur.rowcount)

    def force_reupload(self, local_paths: list[str]) -> int:
        if not local_paths:
            return 0
        now = _utc_now()
        placeholders = ",".join("?" for _ in local_paths)
        sql = f"""
            UPDATE migration_files
            SET status = 'pending',
                error_message = NULL,
                started_at = NULL,
                completed_at = NULL,
                verified_at = NULL,
                updated_at = ?
            WHERE local_path IN ({placeholders})
              AND status IN ('completed', 'verified', 'failed')
        """
        cur = self._conn.execute(sql, [now, *local_paths])
        self._conn.commit()
        return int(cur.rowcount)

    def summary_counts(self, *, prefix: str | None = None) -> dict[str, int]:
        sql = "SELECT status, COUNT(*) AS n FROM migration_files"
        params: list[Any] = []
        if prefix is not None:
            sql += " WHERE experiment_prefix = ?"
            params.append(prefix)
        sql += " GROUP BY status"
        rows = self._conn.execute(sql, params).fetchall()
        return {str(r["status"]): int(r["n"]) for r in rows}

    def list_rows(
        self,
        *,
        status: str | None = None,
        prefix: str | None = None,
    ) -> list[dict[str, Any]]:
        sql = "SELECT * FROM migration_files WHERE 1=1"
        params: list[Any] = []
        if status is not None:
            sql += " AND status = ?"
            params.append(status)
        if prefix is not None:
            sql += " AND experiment_prefix = ?"
            params.append(prefix)
        sql += " ORDER BY local_path"
        return [dict(r) for r in self._conn.execute(sql, params).fetchall()]

    def export_completed(self) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT local_path, s3_key, file_size_bytes, sha256, status,
                   completed_at, verified_at
            FROM migration_files
            WHERE status IN ('completed', 'verified')
            ORDER BY local_path
            """
        ).fetchall()
        return [dict(r) for r in rows]

    def close(self) -> None:
        self._conn.close()
