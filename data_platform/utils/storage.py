"""Local dataset storage with explicit package-relative file paths.

Run from the repo root:

    PYTHONPATH=. uv run pytest tests/data_platform/utils/test_storage.py -q
"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

from data_platform.constants import METADATA_FILENAME, PACKAGE_ROOT
from data_platform.models.sync import (
    SyncBlueskyPostModel,
    SyncRedditCommentModel,
    SyncRedditPostModel,
    SyncTwitterPostModel,
)
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.deduplication import DedupeSession
from data_platform.utils.paths import resolve_package_path, to_package_relative
from lib.timestamp_utils import get_current_timestamp

DATA_ROOT = PACKAGE_ROOT / "data"

_CSV_SUFFIX = ".csv"
_PARQUET_SUFFIX = ".parquet"
_TWEET_ID_COLUMN = "tweet_id"
_AUTHOR_ID_COLUMN = "author_id"
_URI_COLUMN = "uri"


@dataclass(frozen=True)
class AppendResult:
    kept: int
    skipped: int


class StorageStage(StrEnum):
    RAW = "raw"
    PREPROCESSED = "preprocessed"
    FEATURES = "features"
    CURATED = "curated"


def _write_csv(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    with output_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _append_csv(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    file_exists = output_path.exists()
    mode = "a" if file_exists else "w"
    with output_path.open(mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def _write_parquet(rows: list[dict[str, Any]], output_path: Path, fieldnames: list[str]) -> None:
    df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=fieldnames)
    df.to_parquet(output_path, index=False)


def _tabular_suffix(path: Path) -> str:
    suffix = path.suffix.lower()
    if suffix not in {_CSV_SUFFIX, _PARQUET_SUFFIX}:
        raise ValueError(f"Unsupported records file suffix: {path.suffix}")
    return suffix


def _metadata_path(relative_run_dir: str) -> Path:
    return resolve_package_path(relative_run_dir) / METADATA_FILENAME


class StorageManager:
    """Read and write dataset records using package-relative file paths."""

    platform: str
    stage: StorageStage
    model: type[BaseModel]
    dataset_id: str

    def __init__(
        self,
        platform: str,
        stage: StorageStage,
        model: type[BaseModel],
        dataset_id: str,
    ) -> None:
        self.platform = platform
        self.stage = stage
        self.model = model
        self.dataset_id = validate_dataset_id(dataset_id)

    @property
    def platform_data_root(self) -> Path:
        return DATA_ROOT / self.platform

    @property
    def root_dir(self) -> Path:
        return DATA_ROOT / self.platform / self.dataset_id / self.stage

    def create_new_run_dir(self, timestamp: str | None = None) -> str:
        """Create a timestamped run directory and return its package-relative path.

        Parameters
        ----------
        timestamp
            Directory name to use. When omitted, the current run timestamp is used.

        Returns
        -------
        str
            POSIX path relative to the data-platform package.
        """
        run_dir = self.root_dir / (timestamp or get_current_timestamp())
        run_dir.mkdir(parents=True, exist_ok=True)
        return to_package_relative(run_dir)

    def latest_run_dir(self) -> str | None:
        """Return the newest timestamped run directory, or None if none exist."""
        if not self.root_dir.exists():
            return None
        run_dirs = [path for path in self.root_dir.iterdir() if path.is_dir()]
        if not run_dirs:
            return None
        return to_package_relative(max(run_dirs, key=lambda path: path.name))

    def all_runs_complete(self) -> bool:
        """Return True if every timestamped run dir has a complete metadata.json.

        A run dir missing metadata.json is treated as incomplete and returns False.
        When metadata contains ``sync_status`` (raw sync runs), it must equal
        ``completed``. Stages without ``sync_status`` only require metadata.json.
        """
        if not self.root_dir.exists():
            return True
        for path in self.root_dir.iterdir():
            if not path.is_dir():
                continue
            meta = path / METADATA_FILENAME
            if not meta.exists():
                return False
            metadata = self.load_run_metadata(to_package_relative(path))
            sync_status = metadata.get("sync_status")
            if sync_status is not None and sync_status != "completed":
                return False
        return True

    def write_records(self, rows: list[dict[str, Any]], relative_file_path: str) -> str:
        """Validate rows and write them to a package-relative csv or parquet file."""
        validated = [self.model.model_validate(row).model_dump() for row in rows]
        out_path = resolve_package_path(relative_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        fieldnames = list(self.model.model_fields.keys())
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            _write_parquet(validated, out_path, fieldnames)
        else:
            _write_csv(validated, out_path, fieldnames)
        return relative_file_path

    def append_records(self, rows: list[dict[str, Any]], relative_file_path: str) -> str:
        """Validate rows and append them to a package-relative csv or parquet file."""
        validated = [self.model.model_validate(row).model_dump() for row in rows]
        out_path = resolve_package_path(relative_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            if out_path.exists():
                existing = pd.read_parquet(out_path)
                new_df = pd.DataFrame(validated)
                if set(existing.columns) != set(new_df.columns):
                    raise ValueError(
                        f"""
                        Schema mismatch: existing={set(existing.columns)}, new={set(new_df.columns)}
                        """
                    )
                combined = pd.concat([existing, new_df], ignore_index=True)
            else:
                combined = pd.DataFrame(validated)
            combined.to_parquet(out_path, index=False)
        else:
            fieldnames = list(self.model.model_fields.keys())
            _append_csv(validated, out_path, fieldnames)
        return relative_file_path

    def load_seen_ids_from_disk(self, relative_file_path: str, id_column: str) -> set[str]:
        """Return id values already stored in a package-relative records file."""
        out_path = resolve_package_path(relative_file_path)
        if not out_path.exists():
            return set()
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            df = pd.read_parquet(out_path, columns=[id_column])
            return {str(v) for v in df[id_column] if v}
        with out_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return {row[id_column] for row in reader if row.get(id_column)}

    def load_seen_ids_from_all_runs(self, id_column: str, file_name: str) -> set[str]:
        """Union ids from the named file in every timestamped run dir under this stage."""
        if not self.root_dir.exists():
            return set()
        seen: set[str] = set()
        for run_dir in self.root_dir.iterdir():
            if run_dir.is_dir():
                relative_file_path = f"{to_package_relative(run_dir)}/{file_name}"
                seen.update(self.load_seen_ids_from_disk(relative_file_path, id_column))
        return seen

    def append_deduped_records(
        self,
        rows: list[dict[str, Any]],
        relative_file_path: str,
        *,
        dedupe_session: DedupeSession,
    ) -> AppendResult:
        """Append rows whose ids are not already in the dedupe session."""
        kept_rows, skipped = dedupe_session.filter_rows(rows)
        if kept_rows:
            self.append_records(kept_rows, relative_file_path)
            dedupe_session.note_appended(kept_rows)
        return AppendResult(kept=len(kept_rows), skipped=skipped)

    def load_seen_uris(self, relative_file_path: str) -> set[str]:
        """Return uri values already stored in a package-relative records file."""
        return self.load_seen_ids_from_disk(relative_file_path, _URI_COLUMN)

    def load_records(self, relative_file_path: str) -> pd.DataFrame:
        """Load a package-relative csv or parquet records file."""
        out_path = resolve_package_path(relative_file_path)
        if not out_path.exists():
            raise FileNotFoundError(f"Records file not found: {out_path}")
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            return pd.read_parquet(out_path)
        return pd.read_csv(out_path, keep_default_na=False)

    def write_dataframe(self, df: pd.DataFrame, relative_file_path: str) -> str:
        """Write a dataframe to a package-relative csv or parquet file."""
        out_path = resolve_package_path(relative_file_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            df.to_parquet(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)
        return relative_file_path

    def write_run_metadata(self, relative_run_dir: str, metadata: dict[str, Any]) -> str:
        """Write metadata.json under a package-relative run directory."""
        metadata_path = _metadata_path(relative_run_dir)
        metadata_path.parent.mkdir(parents=True, exist_ok=True)
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return to_package_relative(metadata_path)

    def write_run_metadata_atomic(self, relative_run_dir: str, metadata: dict[str, Any]) -> str:
        """Atomically write metadata.json under a package-relative run directory."""
        run_dir = resolve_package_path(relative_run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
        metadata_path = run_dir / METADATA_FILENAME
        tmp_path = run_dir / f"{METADATA_FILENAME}.tmp"
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        tmp_path.replace(metadata_path)
        return to_package_relative(metadata_path)

    def load_run_metadata(self, relative_run_dir: str) -> dict[str, Any]:
        """Load metadata.json from a package-relative run directory."""
        metadata_path = _metadata_path(relative_run_dir)
        if not metadata_path.exists():
            raise FileNotFoundError(f"Metadata file not found: {metadata_path}")
        with metadata_path.open(encoding="utf-8") as f:
            return json.load(f)


class BlueskyStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
    ) -> None:
        super().__init__(
            "bluesky",
            stage,
            SyncBlueskyPostModel,
            dataset_id,
        )


class RedditStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
        model: type[BaseModel] | None = None,
    ) -> None:
        super().__init__(
            "reddit",
            stage,
            model or SyncRedditCommentModel,
            dataset_id,
        )

    def comment_storage(self) -> RedditStorageManager:
        return RedditStorageManager(
            self.stage,
            self.dataset_id,
            model=SyncRedditCommentModel,
        )

    def post_storage(self) -> RedditStorageManager:
        return RedditStorageManager(
            self.stage,
            self.dataset_id,
            model=SyncRedditPostModel,
        )


class TwitterStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
    ) -> None:
        super().__init__(
            "twitter",
            stage,
            SyncTwitterPostModel,
            dataset_id,
        )

    def load_records(self, relative_file_path: str) -> pd.DataFrame:
        """Load Twitter records, keeping tweet and author ids as strings for csv."""
        out_path = resolve_package_path(relative_file_path)
        if not out_path.exists():
            raise FileNotFoundError(f"Records file not found: {out_path}")
        suffix = _tabular_suffix(out_path)
        if suffix == _PARQUET_SUFFIX:
            return pd.read_parquet(out_path)
        return pd.read_csv(
            out_path,
            keep_default_na=False,
            dtype={_TWEET_ID_COLUMN: "string", _AUTHOR_ID_COLUMN: "string"},
        )

    def load_seen_tweet_ids(self, relative_file_path: str) -> set[str]:
        """Return tweet_id values already stored in a package-relative records file."""
        return self.load_seen_ids_from_disk(relative_file_path, _TWEET_ID_COLUMN)
