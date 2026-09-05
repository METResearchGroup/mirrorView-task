"""Shared preprocessing pipeline for platform entrypoints."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, NamedTuple

import pandas as pd
from pydantic import BaseModel

from data_platform.ingestion.data_dumps.bluesky.load_raw import load_hive_dump_posts
from data_platform.preprocessing.sample import sample_records
from data_platform.utils.dataset import dataset_root, relative_run_path, validate_dataset_id
from data_platform.utils.deduplication import DedupeConfig, DedupeSession
from data_platform.preprocessing.previously_used_stimuli import (
    filter_previously_used_stimuli,
    load_previously_used_stimuli_ids,
)
from data_platform.preprocessing.shared_columns import (
    add_standardized_author_columns,
    add_standardized_source_record_id,
)
from data_platform.utils.platform_specific_columns import (
    STANDARDIZED_TEXT_COLUMN,
    PlatformSpecificColumns,
)
from data_platform.utils.storage import StorageManager, StorageStage
from shared.data.registry import DATASETS

TextValidator = Callable[[str], bool]
TextTransform = Callable[[str], str]
RowValidator = Callable[[str], bool]

StorageManagerFactory = Callable[..., StorageManager]

AUTHOR_COLUMN = "author"


class DuplicateFilterResult(NamedTuple):
    """The remaining preprocess rows, plus skip counts for ids that were already seen.

    ``skipped_already_preprocessed`` counts rows dropped because they were
    already written in a prior preprocessed run. ``skipped_previously_used_stimuli``
    counts rows dropped because ``record_id`` matches a study stimuli key.
    Drops from collapsing duplicate ids in the current batch are not counted.
    """

    records: pd.DataFrame
    skipped_already_preprocessed: int
    skipped_previously_used_stimuli: int


@dataclass(frozen=True)
class PreprocessPlatformSpec:
    """Platform-specific configuration for the shared preprocessing pipeline."""
    platform: str
    storage_cls: StorageManagerFactory
    model_cls: type[BaseModel]
    columns: PlatformSpecificColumns
    text_validators: tuple[TextValidator, ...]
    author_handle_source_column: str
    row_validators: tuple[RowValidator, ...] = ()
    text_transforms: tuple[TextTransform, ...] = ()
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
    """The function runs each text transform on the text column of every row.

    The functions run in list order. If ``spec.text_transforms`` is empty, or if
    the frame is empty, the function returns the input frame unchanged.

    Parameters
    ----------
    spec
        Each function in ``text_transforms`` is applied to values in
        ``spec.columns.text_column``.

    Returns
    -------
    pd.DataFrame
        A new frame whose text column has been rewritten when
        ``text_transforms`` has at least one function. Otherwise the function
        returns the original frame.
    """
    if not spec.text_transforms or df.empty:
        return df
    out = df.copy()
    text_col = spec.columns.text_column
    for transform in spec.text_transforms:
        out[text_col] = out[text_col].map(lambda value, fn=transform: fn(str(value)))
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


def apply_integration_specific_filters(df: pd.DataFrame, spec: PreprocessPlatformSpec) -> pd.DataFrame:
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


HIVE_DATE_PREFIX = "date="


def _has_hive_dump_partitions(run_dir: Path) -> bool:
    return any(
        path.is_dir() and path.name.startswith(HIVE_DATE_PREFIX)
        for path in run_dir.iterdir()
    )


def _validated_rows_from_run(
    run_dir: Path,
    spec: PreprocessPlatformSpec,
    raw_storage: StorageManager,
) -> list[dict[str, Any]]:
    records_path = run_dir / raw_storage.records_filename
    if records_path.exists():
        df = raw_storage.load_records(run_dir=run_dir)
        if df.empty:
            return []
        return _rows_to_validated_dicts(df.to_dict(orient="records"), spec.model_cls)
    if _has_hive_dump_partitions(run_dir):
        return load_hive_dump_posts(run_dir, run_dir.name)
    return []


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
        validated_rows.extend(_validated_rows_from_run(run_dir, spec, raw_storage))

    records = (
        pd.DataFrame(validated_rows)
        if validated_rows
        else pd.DataFrame(columns=list(spec.model_cls.model_fields.keys()))
    )
    return records, run_dirs


def _with_sample_metadata(
    metadata: dict[str, Any],
    records: pd.DataFrame,
    sample_size: int | None,
) -> dict[str, Any]:
    if sample_size is None:
        return metadata
    metadata["row_counts"]["sampled"] = len(records)
    metadata["sample_size"] = sample_size
    return metadata


def export_preprocessed_records(
    records: pd.DataFrame,
    spec: PreprocessPlatformSpec,
    dataset_id: str,
    input_count: int,
    *,
    source_raw_run_dirs: list[Path],
    sample_size: int | None = None,
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
    metadata = _with_sample_metadata(metadata, records, sample_size)
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
    stimuli_ids: set[str],
) -> DuplicateFilterResult:
    """Drop already-preprocessed ids, previously used stimuli, and in-batch duplicates.

    Returns
    -------
    DuplicateFilterResult
        Surviving records, the already-preprocessed skip count, and the
        previously used stimuli skip count. Drops from collapsing duplicate
        ids in the current batch are not counted.
    """
    if records.empty:
        return DuplicateFilterResult(records.copy(), 0, 0)

    id_col = spec.columns.records_id_column
    dedupe_session = DedupeSession(DedupeConfig(id_column=id_col))
    preprocessed_storage = spec.storage_cls(StorageStage.PREPROCESSED, dataset_id)
    dedupe_session.load_seen_ids_from_all_runs(preprocessed_storage)

    is_new = ~records[id_col].isin(list(dedupe_session.seen_ids))
    skipped = len(records) - int(is_new.sum())
    kept = records.loc[is_new].reset_index(drop=True)
    kept, skipped_stimuli = filter_previously_used_stimuli(kept, stimuli_ids)
    output = collapse_candidates_by_id(kept, id_col, keep="last")
    return DuplicateFilterResult(output, skipped, skipped_stimuli)


def apply_integration_specific_preprocessing(
    df: pd.DataFrame,
    spec: PreprocessPlatformSpec,
) -> pd.DataFrame:
    """Apply platform-specific text transforms before filtering."""
    return apply_text_transform(df, spec)


def preprocess_records(
    dataset_id: str,
    spec: PreprocessPlatformSpec,
    sample_size: int | None = None,
) -> Path:
    """Run the full preprocessing pipeline for one dataset and persist the result.

    The function loads all completed raw runs and adds standardized columns.
    It then drops rows seen in prior preprocessed runs, rows already used as
    study stimuli, and duplicate ids within the batch. After that, it applies
    platform-specific text transforms and validators, optionally samples the
    kept rows, and it writes a new preprocessed run directory. It also prints a
    one-line keep and skip summary to stdout.

    Parameters
    ----------
    dataset_id
        Dataset identifier in ``{platform}_{uuid}`` form.
    spec
        Platform-specific preprocess configuration.
    sample_size
        Maximum kept rows to write. ``None`` writes every kept row.

    Returns
    -------
    pathlib.Path
        Path to the new preprocessed run directory.

    Raises
    ------
    ValueError
        If ``dataset_id`` is malformed.
    FileNotFoundError
        When no raw runs exist for the dataset, or a registered stimuli CSV
        is missing.
    RuntimeError
        When a raw run is incomplete.
    KeyError
        When a required source column is missing during standardization.
    """
    dataset_id = validate_dataset_id(dataset_id)
    records, source_raw_run_dirs = load_raw_records(spec, dataset_id)
    records = add_standardized_columns(records, spec)
    stimuli_ids = load_previously_used_stimuli_ids(DATASETS)
    filtered = filter_duplicate_records(records, spec, dataset_id, stimuli_ids)
    records = filtered.records
    skipped = filtered.skipped_already_preprocessed
    skipped_stimuli = filtered.skipped_previously_used_stimuli
    input_count = len(records)
    records = apply_integration_specific_preprocessing(records, spec)
    records = apply_integration_specific_filters(records, spec)
    if sample_size is not None:
        records = sample_records(records, sample_size)
    output_dir = export_preprocessed_records(
        records,
        spec,
        dataset_id,
        input_count=input_count,
        source_raw_run_dirs=source_raw_run_dirs,
        sample_size=sample_size,
    )
    print(
        f"preprocess_records: kept {len(records)} of {input_count}"
        f" (skipped {skipped} already in a prior preprocessed run,"
        f" skipped {skipped_stimuli} already used as stimuli) -> {output_dir}"
    )
    return output_dir
