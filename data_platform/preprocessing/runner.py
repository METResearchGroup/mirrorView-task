"""Shared preprocessing pipeline for platform entrypoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, cast

import pandas as pd
from pydantic import BaseModel

from data_platform.constants import COMMENTS_FILENAME, POSTS_FILENAME
from data_platform.utils.dataset import validate_dataset_id
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.utils.gate_checks import require_all_runs_complete
from data_platform.utils.paths import resolve_package_path, to_package_relative
from data_platform.utils.platform_specific_columns import PlatformSpecificColumns
from data_platform.utils.storage import StorageManager, StorageStage

TextValidator = Callable[[str], bool]
RowValidator = Callable[[str], bool]

StorageManagerFactory = Callable[..., StorageManager]

AUTHOR_COLUMN = "author"
_COMMENTS_KEY = "comments"


def _records_file_name(spec: PreprocessPlatformSpec) -> str:
    if spec.columns.records_file_key == _COMMENTS_KEY:
        return COMMENTS_FILENAME
    return POSTS_FILENAME


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
) -> tuple[pd.DataFrame, list[str]]:
    """Load raw records from all run dirs for preprocessing.

    Returns both the loaded/validated records and the package-relative raw run
    directories they came from.
    """
    raw_storage = spec.storage_cls(StorageStage.RAW, dataset_id)
    raw_root = raw_storage.root_dir
    file_name = _records_file_name(spec)
    run_dirs = sorted([p for p in raw_root.iterdir() if p.is_dir()])
    relative_run_dirs = [to_package_relative(path) for path in run_dirs]
    validated_rows: list[dict[str, Any]] = []
    for relative_run_dir in relative_run_dirs:
        relative_file_path = f"{relative_run_dir}/{file_name}"
        if not resolve_package_path(relative_file_path).exists():
            continue
        df = raw_storage.load_records(relative_file_path)
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
    return records, relative_run_dirs


def save_preprocessed(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
    dataset_id: str,
    input_count: int,
    *,
    source_raw_run_dirs: list[str],
) -> str:
    """Persist preprocessed records to a new timestamped run directory."""
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    file_name = _records_file_name(spec)

    output_dir = preprocessed_storage.create_new_run_dir()
    preprocessed_storage.write_records(
        records.to_dict(orient="records"),
        f"{output_dir}/{file_name}",
    )
    source_raw_runs = list(source_raw_run_dirs)
    source_raw_run = source_raw_runs[-1] if source_raw_runs else None
    metadata: dict[str, Any] = {
        "dataset_id": dataset_id,
        "source_raw_run": (source_raw_run),
        "source_raw_runs": source_raw_runs,
        "preprocess_timestamp": output_dir.rsplit("/", 1)[-1],
        "row_counts": {
            "input": input_count,
            "output": len(records),
        },
        "files": {
            spec.columns.records_file_key: file_name,
        },
    }
    preprocessed_storage.write_run_metadata(output_dir, metadata)
    return output_dir


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
) -> str:
    dataset_id = validate_dataset_id(dataset_id)
    raw_storage = spec.storage_cls(StorageStage.RAW, dataset_id)
    if raw_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No raw runs found for dataset {dataset_id}")
    require_all_runs_complete(raw_storage, dataset_id)
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    file_name = _records_file_name(spec)
    dedupe_session = DedupeSession(
        DedupeConfig(
            id_column=spec.columns.records_id_column,
            filename=file_name,
            include_prior_runs=True,
        )
    )
    warm_path = f"{to_package_relative(preprocessed_storage.root_dir)}/{file_name}"
    dedupe_session.warm(preprocessed_storage, warm_path)

    records, source_raw_run_dirs = load_raw_records(spec, dataset_id)
    records, skipped = _drop_already_preprocessed(
        records, spec.columns.records_id_column, dedupe_session.seen_ids
    )

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
