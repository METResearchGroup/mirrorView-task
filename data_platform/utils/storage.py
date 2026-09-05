from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

from data_platform.ingestion.generate_record_id import (
    RECORD_ID_COLUMN,
    attach_record_id,
)
from data_platform.models.sync import (
    PreprocessedBlueskyPostModel,
    PreprocessedRedditCommentModel,
    PreprocessedTwitterPostModel,
    SyncBlueskyPostModel,
    SyncRedditCommentModel,
    SyncTwitterPostModel,
)
from data_platform.utils.dataset import ValidDataFormats, load_dataset_format, validate_dataset_id
from data_platform.utils.deduplication import DedupeSession
from data_platform.utils.object_store import ObjectStore, resolve_object_store
from lib.timestamp_utils import get_current_timestamp

DATA_ROOT = Path(__file__).resolve().parents[1] / "data"
METADATA_FILENAME = "metadata.json"
RECORDS_NOT_FOUND_MESSAGE = "Records file not found"
METADATA_NOT_FOUND_MESSAGE = "Metadata file not found"
MISSING_STAGE_RUNS_MESSAGE = (
    "No {stage} runs found for dataset {dataset_id} under {root}"
)
INCOMPLETE_STAGE_RUNS_MESSAGE = (
    "Not all {stage} runs for dataset {dataset_id} are complete locally"
)


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


class StorageManager:
    platform: str
    stage: StorageStage
    model: type[BaseModel]
    records_filename: str
    dataset_id: str
    _store: ObjectStore

    def __init__(
        self,
        platform: str,
        stage: StorageStage,
        model: type[BaseModel],
        dataset_id: str,
        *,
        records_filename: str,
    ) -> None:
        self.platform = platform
        self.stage = stage
        self.model = model
        self.dataset_id = validate_dataset_id(dataset_id)
        self.format: ValidDataFormats = load_dataset_format(platform, dataset_id)
        stem = Path(records_filename).stem
        self.records_filename = f"{stem}.{self.format.value}"
        self._store = resolve_object_store(local_root=DATA_ROOT)

    @property
    def platform_data_root(self) -> Path:
        return DATA_ROOT / self.platform

    @property
    def root_dir(self) -> Path:
        return DATA_ROOT / self.platform / self.dataset_id / self.stage

    def _key_for(self, path: Path) -> str:
        """Return the object store key for a path under ``DATA_ROOT``, e.g. ``bluesky/{dataset_id}/raw/{run}/posts.parquet``.

        Raises
        ------
        ValueError
            When ``path`` is not under ``DATA_ROOT``.
        """
        try:
            return path.relative_to(DATA_ROOT).as_posix()
        except ValueError as e:
            raise ValueError(f"Path {path} is not under the data root {DATA_ROOT}") from e

    def _read_object(self, path: Path, *, missing_message: str) -> bytes:
        try:
            return self._store.get_bytes(self._key_for(path))
        except FileNotFoundError as e:
            raise FileNotFoundError(f"{missing_message}: {path}") from e

    def create_new_run_dir(self, timestamp: str | None = None) -> Path:
        run_dir = self.root_dir / (timestamp or get_current_timestamp())
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def latest_run_dir(self) -> Path | None:
        if not self.root_dir.exists():
            return None
        run_dirs = [path for path in self.root_dir.iterdir() if path.is_dir()]
        if not run_dirs:
            return None
        return max(run_dirs, key=lambda path: path.name)

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
            metadata = self.load_run_metadata(path)
            sync_status = metadata.get("sync_status")
            if sync_status is not None and sync_status != "completed":
                return False
        return True

    def _resolve_run_dir(
        self,
        run_dir: Path | None,
        *,
        latest: bool,
    ) -> Path:
        if run_dir is not None:
            return run_dir
        if latest:
            resolved = self.latest_run_dir()
            if resolved is None:
                raise FileNotFoundError(f"No {self.stage} runs found under {self.root_dir}")
            return resolved
        raise ValueError("Either run_dir must be provided or latest=True")

    def _prepare_rows_for_write(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Return rows with ``record_id`` filled in from the platform primary key.

        Feature label rows are keyed by ``source_record_id`` and hold no
        platform primary key, so the feature stage keeps its rows as they are.
        """
        if self.stage == StorageStage.FEATURES:
            return rows
        prepared: list[dict[str, Any]] = []
        for row in rows:
            if row.get(RECORD_ID_COLUMN):
                prepared.append(row)
            else:
                prepared.append(attach_record_id(row, self.platform))
        return prepared

    def write_records(
        self,
        rows: list[dict[str, Any]],
        run_dir: Path,
        *,
        filename: str | None = None,
    ) -> Path:
        validated = [
            self.model.model_validate(row).model_dump()
            for row in self._prepare_rows_for_write(rows)
        ]
        out_path = run_dir / (filename or self.records_filename)
        fieldnames = list(self.model.model_fields.keys())
        if self.format == "parquet":
            _write_parquet(validated, out_path, fieldnames)
        else:
            _write_csv(validated, out_path, fieldnames)
        return out_path

    def append_records(
        self,
        rows: list[dict[str, Any]],
        run_dir: Path,
        *,
        filename: str | None = None,
    ) -> Path:
        validated = [
            self.model.model_validate(row).model_dump()
            for row in self._prepare_rows_for_write(rows)
        ]
        out_path = run_dir / (filename or self.records_filename)
        if self.format == "parquet":
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
        return out_path

    def load_seen_ids_from_disk(
        self,
        run_dir: Path,
        id_column: str,
        *,
        filename: str | None = None,
    ) -> set[str]:
        out_path = run_dir / (filename or self.records_filename)
        if not out_path.exists():
            return set()
        if self.format == "parquet":
            df = pd.read_parquet(out_path, columns=[id_column])
            return {str(v) for v in df[id_column] if v}
        with out_path.open(newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            return {row[id_column] for row in reader if row.get(id_column)}

    def load_seen_ids_from_all_runs(
        self,
        id_column: str,
        *,
        filename: str | None = None,
    ) -> set[str]:
        """Union ids from every timestamped run dir under this stage root."""
        if not self.root_dir.exists():
            return set()
        seen: set[str] = set()
        for run_dir in self.root_dir.iterdir():
            if run_dir.is_dir():
                seen.update(
                    self.load_seen_ids_from_disk(
                        run_dir, id_column, filename=filename
                    )
                )
        return seen

    def append_deduped_records(
        self,
        rows: list[dict[str, Any]],
        run_dir: Path,
        *,
        dedupe_session: DedupeSession,
        filename: str | None = None,
    ) -> AppendResult:
        kept_rows, skipped = dedupe_session.exclude_seen_ids(rows)
        resolved_filename = filename or dedupe_session.config.filename
        if kept_rows:
            self.append_records(kept_rows, run_dir, filename=resolved_filename)
            dedupe_session.add_seen_ids(kept_rows)
        return AppendResult(kept=len(kept_rows), skipped=skipped)

    def load_records(
        self,
        run_dir: Path | None = None,
        *,
        latest: bool = False,
        filename: str | None = None,
    ) -> pd.DataFrame:
        resolved_run_dir = self._resolve_run_dir(run_dir, latest=latest)
        out_path = resolved_run_dir / (filename or self.records_filename)
        body = self._read_object(out_path, missing_message=RECORDS_NOT_FOUND_MESSAGE)
        if self.format == "parquet":
            return pd.read_parquet(BytesIO(body))
        return pd.read_csv(BytesIO(body), keep_default_na=False)

    def write_dataframe(
        self,
        df: pd.DataFrame,
        run_dir: Path,
        *,
        filename: str | None = None,
    ) -> Path:
        out_path = run_dir / (filename or self.records_filename)
        if self.format == "parquet":
            df.to_parquet(out_path, index=False)
        else:
            df.to_csv(out_path, index=False)
        return out_path

    def write_run_metadata(self, run_dir: Path, metadata: dict[str, Any]) -> Path:
        metadata_path = run_dir / METADATA_FILENAME
        with metadata_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        return metadata_path

    def write_run_metadata_atomic(self, run_dir: Path, metadata: dict[str, Any]) -> Path:
        metadata_path = run_dir / METADATA_FILENAME
        tmp_path = run_dir / f"{METADATA_FILENAME}.tmp"
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)
        tmp_path.replace(metadata_path)
        return metadata_path

    def filename_for(self, stem: str) -> str:
        """Return the format-correct filename for a given stem."""
        return f"{stem}.{self.format.value}"

    def require_all_runs_complete(self, dataset_id: str) -> None:
        """Raise when this stage has no run directory or an incomplete run.

        Parameters
        ----------
        dataset_id
            Dataset id used in the error text.

        Raises
        ------
        RuntimeError
            When the stage root is missing or a timestamped run is incomplete.
        """
        if not self.root_dir.exists():
            raise RuntimeError(
                MISSING_STAGE_RUNS_MESSAGE.format(
                    stage=self.stage,
                    dataset_id=dataset_id,
                    root=self.root_dir,
                )
            )
        if not self.all_runs_complete():
            raise RuntimeError(
                INCOMPLETE_STAGE_RUNS_MESSAGE.format(
                    stage=self.stage,
                    dataset_id=dataset_id,
                )
            )

    def load_run_metadata(
        self,
        run_dir: Path | None = None,
        *,
        latest: bool = False,
    ) -> dict[str, Any]:
        resolved_run_dir = self._resolve_run_dir(run_dir, latest=latest)
        metadata_path = resolved_run_dir / METADATA_FILENAME
        body = self._read_object(metadata_path, missing_message=METADATA_NOT_FOUND_MESSAGE)
        return json.loads(body.decode("utf-8"))


class BlueskyStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
        *,
        records_filename: str = "posts.csv",
        model: type[BaseModel] | None = None,
    ) -> None:
        if model is None and stage == StorageStage.PREPROCESSED:
            resolved_model: type[BaseModel] = PreprocessedBlueskyPostModel
        else:
            resolved_model = model or SyncBlueskyPostModel
        super().__init__(
            "bluesky",
            stage,
            resolved_model,
            dataset_id,
            records_filename=records_filename,
        )


class RedditStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
        *,
        records_filename: str = "comments.csv",
        model: type[BaseModel] | None = None,
    ) -> None:
        if model is None and stage == StorageStage.PREPROCESSED:
            resolved_model: type[BaseModel] = PreprocessedRedditCommentModel
        else:
            resolved_model = model or SyncRedditCommentModel
        super().__init__(
            "reddit",
            stage,
            resolved_model,
            dataset_id,
            records_filename=records_filename,
        )


class TwitterStorageManager(StorageManager):
    def __init__(
        self,
        stage: StorageStage = StorageStage.RAW,
        dataset_id: str = "",
        *,
        records_filename: str = "posts.csv",
        model: type[BaseModel] | None = None,
    ) -> None:
        if model is None and stage == StorageStage.PREPROCESSED:
            resolved_model: type[BaseModel] = PreprocessedTwitterPostModel
        else:
            resolved_model = model or SyncTwitterPostModel
        super().__init__(
            "twitter",
            stage,
            resolved_model,
            dataset_id,
            records_filename=records_filename,
        )

    def load_records(
        self,
        run_dir: Path | None = None,
        *,
        latest: bool = False,
        filename: str | None = None,
    ) -> pd.DataFrame:
        resolved_run_dir = self._resolve_run_dir(run_dir, latest=latest)
        csv_path = resolved_run_dir / (filename or self.records_filename)
        body = self._read_object(csv_path, missing_message=RECORDS_NOT_FOUND_MESSAGE)

        return pd.read_csv(
            BytesIO(body),
            keep_default_na=False,
            dtype={
                "tweet_id": "string",
                "author_id": "string",
                "author_handle": "string",
                "source_record_id": "string",
            },
        )
