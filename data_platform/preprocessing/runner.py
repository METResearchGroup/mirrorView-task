"""Shared preprocessing pipeline for platform entrypoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel

from data_platform.utils.dataset import dataset_root, relative_run_path, validate_dataset_id
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.preprocessing.shared_columns import (
    add_standardized_author_columns,
    add_standardized_source_record_id,
)
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_TEXT_COLUMN,
    PlatformSpecificColumns,
)
from data_platform.utils.storage import StorageManager, StorageStage

TextValidator = Callable[[str], bool]
RowValidator = Callable[[str], bool]

StorageManagerFactory = Callable[..., StorageManager]

AUTHOR_COLUMN = "author"


@dataclass(frozen=True)
class PreprocessPlatformSpec:
    """Platform-specific configuration for the shared preprocessing pipeline.

    Bundles storage access, record models, column names, validators, and
    optional text transforms so platform entrypoints can delegate to
    :func:`preprocess_records` without reimplementing the flow.
    """
    platform: str
    storage_cls: StorageManagerFactory
    model_cls: type[BaseModel]
    columns: PlatformSpecificColumns
    text_validators: tuple[TextValidator, ...]
    author_handle_source_column: str
    row_validators: tuple[RowValidator, ...] = ()
    text_transform: Callable[[str], str] | None = None
    original_platform_text_column: str = STANDARDIZED_TEXT_COLUMN


def add_standardized_text_column(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Copy the platform's original post or comment text onto the shared ``text`` column.

    You still have original fields such as Reddit ``body`` on the returned frame.
    The function does not modify the input frame.

    Parameters
    ----------
    spec
        ``original_platform_text_column`` is the copy source. The destination is
        always shared ``text``.

    Returns
    -------
    pd.DataFrame
        A new frame that includes ``text``.

    Raises
    ------
    KeyError
        When ``spec.original_platform_text_column`` is missing from the frame.
    """
    out = df.copy()
    original_platform_text = out[spec.original_platform_text_column]
    out[STANDARDIZED_TEXT_COLUMN] = original_platform_text.map(lambda value: str(value))
    return out


def apply_text_transform(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Apply the platform's optional text transform to each row's text column.

    When ``spec.text_transform`` is unset or the frame is empty, the input
    frame is returned unchanged.

    Parameters
    ----------
    spec
        ``text_transform`` is applied to values in ``spec.columns.text_column``.

    Returns
    -------
    pd.DataFrame
        A new frame with transformed text when a transform is configured;
        otherwise the original frame.
    """
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
    """Return whether every text validator accepts the given string.

    An empty ``validators`` sequence is treated as passing.
    """
    return all(validator(text) for validator in validators)


def passes_row_validators(
    author: str,
    validators: Sequence[RowValidator],
) -> bool:
    """Return whether every row validator accepts the given author value.

    An empty ``validators`` sequence is treated as passing.
    """
    return all(validator(author) for validator in validators)


def filter_records(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame:
    """Return only rows whose text (and optional author) pass every validator."""
    if df.empty:
        return df.copy()

    prepared = df
    if spec.columns.text_column not in df.columns:
        prepared = add_standardized_text_column(df, spec)
    text_col = spec.columns.text_column
    text_mask = prepared[text_col].map(
        lambda value: passes_all_validators(str(value), spec.text_validators)
    )
    if not spec.row_validators:
        return prepared.loc[text_mask].reset_index(drop=True)

    author_mask = prepared[AUTHOR_COLUMN].map(
        lambda value: passes_row_validators(str(value), spec.row_validators)
    )
    return prepared.loc[text_mask & author_mask].reset_index(drop=True)


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

    Returns both the loaded/validated records and the raw run directories they
    came from.

    Raises
    ------
    FileNotFoundError
        When no raw run directories exist for the dataset.
    RuntimeError
        When a raw run is incomplete (via ``require_all_runs_complete``).
    """
    raw_storage = spec.storage_cls(StorageStage.RAW, dataset_id)
    if raw_storage.latest_run_dir() is None:
        raise FileNotFoundError(f"No raw runs found for dataset {dataset_id}")
    raw_storage.require_all_runs_complete(dataset_id)
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
    df: pd.DataFrame, id_col: str, keep: str = "last"
) -> pd.DataFrame:
    """Keep one row per id, and keep the later row when keep is last.

    Parameters
    ----------
    df
        Candidate records after known ids have already been dropped.
    id_col
        Column that identifies a post or comment.
    keep
        Which duplicate to keep. ``last`` means the later raw row wins.

    Returns
    -------
    pd.DataFrame
        The frame has one row per id, and the index is reset.
    """
    return df.drop_duplicates(subset=[id_col], keep=keep).reset_index(drop=True)


def add_standardized_columns(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Add shared ``text``, ``author_handle``, and ``source_record_id`` columns.

    Values are copied from platform-specific source columns named on ``spec``.
    Original platform columns are preserved. The input frame is not modified.

    Parameters
    ----------
    spec
        Names the source columns for text, author handle, and record id.

    Returns
    -------
    pd.DataFrame
        A new frame with the three standardized columns added.

    Raises
    ------
    KeyError
        When a required source column is missing from the frame.
    """
    records = add_standardized_text_column(records, spec)
    records = add_standardized_author_columns(records, spec)
    records = add_standardized_source_record_id(records, spec)
    return records


def filter_duplicate_records(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
    dataset_id: str,
) -> tuple[pd.DataFrame, int]:
    """Drop rows whose id appears in prior preprocessed runs, then collapse duplicates.

    Loads seen ids from every preprocessed run (4a), drops matching rows, and
    counts those drops as ``skipped``. Collapses remaining duplicate ids within
    the candidate batch, keeping the last row per id (4b). Stimuli-skip dedupe
    (4c) is out of scope.

    Returns
    -------
    tuple[pd.DataFrame, int]
        Surviving records and the 4a-only skip count (collapse drops excluded).
    """
    if records.empty:
        return records.copy(), 0

    id_col = spec.columns.records_id_column
    dedupe_session = DedupeSession(DedupeConfig(id_column=id_col))
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    dedupe_session.load_seen_ids_from_all_runs(preprocessed_storage)

    is_new = ~records[id_col].isin(list(dedupe_session.seen_ids))
    skipped = len(records) - int(is_new.sum())
    kept = records.loc[is_new].reset_index(drop=True)
    surviving = collapse_candidates_by_id(kept, id_col, keep="last")
    return surviving, skipped


def apply_integration_specific_preprocessing(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Apply platform-specific text transforms before filtering.

    Delegates to :func:`apply_text_transform`. When ``spec.text_transform`` is
    set (Twitter sets ``strip_tco_links`` to remove ``t.co`` URLs), the
    transform runs on ``spec.columns.text_column``. Empty frames and specs
    without a transform are returned unchanged.
    """
    return apply_text_transform(df, spec)


def apply_integration_specific_filters(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Apply platform-specific row/text validators after preprocessing.

    Delegates to :func:`filter_records`. Each row must pass every
    ``spec.text_validators`` on ``spec.columns.text_column``. When
    ``spec.row_validators`` is non-empty, the ``author`` column must pass
    those validators as well. Empty frames are returned unchanged.
    """
    return filter_records(df, spec)


def export_preprocessed_records(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
    dataset_id: str,
    input_count: int,
    *,
    source_raw_run_dirs: list[Path],
) -> Path:
    """Persist preprocessed records to a new timestamped run directory.

    Creates a new preprocessed run, writes the records file, and saves run
    metadata including ``dataset_id``, ``source_raw_runs``, and ``row_counts``
    (``input`` from ``input_count``, ``output`` from surviving rows).

    Returns
    -------
    Path
        The new preprocessed run directory path.
    """
    return save_preprocessed(
        records,
        spec,
        dataset_id,
        input_count,
        source_raw_run_dirs=source_raw_run_dirs,
    )


def preprocess_records(
    dataset_id: str,
    spec: PreprocessPlatformSpec,
) -> Path:
    """Run the full preprocessing pipeline for one dataset and persist the result.

    Loads all completed raw runs, adds standardized columns, drops rows seen in
    prior preprocessed runs and duplicate ids within the batch, applies
    platform-specific text transforms and validators, then writes a new
    preprocessed run directory. Also prints a one-line keep/skip summary to
    stdout.

    Parameters
    ----------
    dataset_id
        Dataset identifier in ``{platform}_{uuid}`` form.

    Returns
    -------
    pathlib.Path
        Path to the new preprocessed run directory.

    Raises
    ------
    ValueError
        If ``dataset_id`` is malformed.
    FileNotFoundError
        When no raw runs exist for the dataset.
    RuntimeError
        When a raw run is incomplete.
    KeyError
        When a required source column is missing during standardization.

    Notes
    -----
    Does not skip records already used as experiment stimuli (README step 4c).
    """
    dataset_id = validate_dataset_id(dataset_id)
    records, source_raw_run_dirs = load_raw_records(spec, dataset_id)
    records = add_standardized_columns(records, spec)
    records, skipped = filter_duplicate_records(records, spec, dataset_id)
    input_count = len(records)
    records = apply_integration_specific_preprocessing(records, spec)
    records = apply_integration_specific_filters(records, spec)
    output_dir = export_preprocessed_records(
        records,
        spec,
        dataset_id,
        input_count=input_count,
        source_raw_run_dirs=source_raw_run_dirs,
    )
    print(
        f"preprocess_records: kept {len(records)} of {input_count}"
        f" (skipped {skipped} already in a prior preprocessed run) -> {output_dir}"
    )
    return output_dir
