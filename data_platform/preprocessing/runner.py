"""Shared preprocessing pipeline for platform entrypoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

import pandas as pd
from pydantic import BaseModel

from data_platform.utils.dataset import dataset_root, relative_run_path, validate_dataset_id
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.gate_checks import require_all_runs_complete
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import StorageManager, StorageStage

TextValidator = Callable[[str], bool]
RowValidator = Callable[[str], bool]

StorageManagerFactory = Callable[..., StorageManager]

AUTHOR_COLUMN = "author"


@dataclass(frozen=True)
class PreprocessPlatformSpec:
    platform: str
    storage_cls: StorageManagerFactory
    model_cls: type[BaseModel]
    columns: PlatformSpecificColumns
    text_validators: tuple[TextValidator, ...]
    row_validators: tuple[RowValidator, ...] = ()
    text_transform: Callable[[str], str] | None = None


def apply_text_transform(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    if spec.text_transform is None or df.empty:
        return df
    out = df.copy()
    text_col = spec.columns.text_column
    transform = spec.text_transform
    out[text_col] = out[text_col].map(lambda v: transform(str(v)))
    return out


def passes_all_validators(
    text: str,
    validators: Sequence[TextValidator],
) -> bool:
    return all(validator(text) for validator in validators)


def passes_row_validators(
    author: str,
    validators: Sequence[RowValidator],
) -> bool:
    return all(validator(author) for validator in validators)


def filter_records(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame:
    """Return only rows whose text (and optional author) pass every validator."""
    if df.empty:
        return df.copy()

    text_col = spec.columns.text_column
    text_mask = df[text_col].map(
        lambda value: passes_all_validators(str(value), spec.text_validators)
    )
    if not spec.row_validators:
        return df.loc[text_mask].reset_index(drop=True)

    author_mask = df[AUTHOR_COLUMN].map(
        lambda value: passes_row_validators(str(value), spec.row_validators)
    )
    return df.loc[text_mask & author_mask].reset_index(drop=True)


def _rows_to_validated_dicts(
    rows: list[dict[str, Any]],
    model_cls: type[BaseModel],
) -> list[dict[str, Any]]:
    return [model_cls.model_validate(row).model_dump() for row in rows]


def load_raw_records(
    spec: PreprocessPlatformSpec,
    dataset_id: str,
) -> tuple[pd.DataFrame, list[Path]]:
    """Load raw records from all run dirs for preprocessing.

    Returns both the loaded/validated records and the raw run directories they came from.
    """
    raw_storage = spec.storage_cls(StorageStage.RAW, dataset_id)
    raw_root = raw_storage.root_dir
    run_dirs = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    validated_rows: list[dict[str, Any]] = []
    for run_dir in run_dirs:
        records_path = run_dir / raw_storage.records_filename
        if not records_path.exists():
            continue
        df = raw_storage.load_records(run_dir=run_dir)
        if df.empty:
            continue
        validated_rows.extend(
            _rows_to_validated_dicts(df.to_dict(orient="records"), spec.model_cls)
        )

    records = (
        pd.DataFrame(validated_rows)
        if validated_rows
        else pd.DataFrame(columns=list(spec.model_cls.model_fields.keys()))
    )
    return records, run_dirs


def save_preprocessed(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
    dataset_id: str,
    input_count: int,
    *,
    source_raw_run_dirs: list[Path],
) -> Path:
    """Persist preprocessed records to a new timestamped run directory."""
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    root = dataset_root(spec.platform, dataset_id)

    output_dir = preprocessed_storage.create_new_run_dir()
    preprocessed_storage.write_records(records.to_dict(orient="records"), output_dir)
    source_raw_runs = [relative_run_path(root, d) for d in source_raw_run_dirs]
    source_raw_run = source_raw_runs[-1] if source_raw_runs else None
    metadata: dict[str, Any] = {
        "dataset_id": dataset_id,
        "source_raw_run": (source_raw_run),
        "source_raw_runs": source_raw_runs,
        "preprocess_timestamp": output_dir.name,
        "row_counts": {
            "input": input_count,
            "output": len(records),
        },
        "files": {
            spec.columns.records_file_key: preprocessed_storage.records_filename,
        },
    }
    preprocessed_storage.write_run_metadata(output_dir, metadata)
    return output_dir


def collapse_candidates_by_id(
    df: pd.DataFrame,
    id_col: str,
    keep: str = "last",
) -> pd.DataFrame:
    """Return one row per id, keeping the last duplicate when keep is "last".

    Preprocess uses keep="last" so a later raw run wins when the same id appears
    more than once in the current batch.

    Parameters
    ----------
    df
        Candidate records after prior-run ids have already been dropped.
    id_col
        Column that identifies a record.
    keep
        Which duplicate to keep. Preprocess callers pass ``"last"``.

    Returns
    -------
    pd.DataFrame
        A new frame with one row per id and a reset index.
    """
    return df.drop_duplicates(subset=[id_col], keep=keep).reset_index(drop=True)


def _drop_already_preprocessed(
    records: pd.DataFrame, id_col: str, seen_ids: set[str]
) -> tuple[pd.DataFrame, int]:
    """Drop rows already preprocessed in a prior run, then dedupe by id within this batch.

    Returns the surviving records and how many rows were dropped for being seen before.
    """
    id_series = cast(pd.Series, records[id_col])
    is_new = ~id_series.isin(list(seen_ids))
    skipped = len(records) - int(is_new.sum())
    deduped = (
        records.loc[is_new].drop_duplicates(subset=[id_col], keep="last").reset_index(drop=True)
    )
    return deduped, skipped


def preprocess_records(
    dataset_id: str,
    spec: PreprocessPlatformSpec,
) -> Path:
    dataset_id = validate_dataset_id(dataset_id)
    raw_storage = spec.storage_cls(StorageStage.RAW, dataset_id)
    if raw_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No raw runs found for dataset {dataset_id}")
    require_all_runs_complete(raw_storage, dataset_id)
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    session = DedupeSession(DedupeConfig(id_column=spec.columns.records_id_column))
    session.load_seen_ids_from_all_runs(preprocessed_storage)

    records, source_raw_run_dirs = load_raw_records(spec, dataset_id)
    id_col = spec.columns.records_id_column
    is_new = ~records[id_col].isin(list(session.seen_ids))
    skipped = len(records) - int(is_new.sum())
    records = records.loc[is_new].reset_index(drop=True)
    records = collapse_candidates_by_id(records, id_col, keep="last")

    preprocessed = apply_text_transform(records, spec)
    preprocessed = filter_records(preprocessed, spec)
    output_dir = save_preprocessed(
        preprocessed,
        spec,
        dataset_id,
        input_count=len(records),
        source_raw_run_dirs=source_raw_run_dirs,
    )
    noun = spec.columns.records_file_key
    print(
        f"preprocess_records: kept {len(preprocessed)} of {len(records)} {noun}"
        f" (skipped {skipped} already preprocessed) -> {output_dir}"
    )
    return output_dir
