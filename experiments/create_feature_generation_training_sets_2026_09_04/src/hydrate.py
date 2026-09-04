"""Join classifier labels to preprocessed records and write training parquets."""

from pathlib import Path

import pandas as pd

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    LABEL_COLUMNS,
    LABEL_TIMESTAMP_COLUMN,
    OUTPUT_ID_COLUMN,
    OUTPUT_TEXT_COLUMN,
    PLATFORM_RECORD_COLUMNS,
)

PARQUET_MAGIC = b"PAR1"
PARQUET_HEADER_BYTES = 4
RECORD_FILENAMES: tuple[str, ...] = (
    "posts.csv",
    "posts.parquet",
    "comments.csv",
    "comments.parquet",
)
PREPROCESSED_DIRNAME = "preprocessed"


def read_table(path: Path) -> pd.DataFrame:
    """Load a label or record table from disk.

    Parameters
    ----------
    path
        Path to a CSV or parquet-backed table file.

    Returns
    -------
    pandas.DataFrame
        Parsed table contents.
    """
    with path.open("rb") as handle:
        header = handle.read(PARQUET_HEADER_BYTES)
    if header == PARQUET_MAGIC:
        return pd.read_parquet(path)
    return pd.read_csv(path, keep_default_na=False)


def _resolve_platform(platform: str) -> tuple[str, str]:
    if platform not in PLATFORM_RECORD_COLUMNS:
        raise ValueError(f"Unknown platform: {platform}")
    return PLATFORM_RECORD_COLUMNS[platform]


def _resolve_classifier(classifier_name: str) -> tuple[str, ...]:
    if classifier_name not in LABEL_COLUMNS:
        raise ValueError(f"Unknown classifier: {classifier_name}")
    return LABEL_COLUMNS[classifier_name]


def _output_columns(classifier_name: str) -> list[str]:
    label_columns = LABEL_COLUMNS[classifier_name]
    return [
        OUTPUT_ID_COLUMN,
        LABEL_TIMESTAMP_COLUMN,
        OUTPUT_TEXT_COLUMN,
        *label_columns,
    ]


def _record_paths(dataset_dir: Path) -> list[Path]:
    preprocessed_dir = dataset_dir / PREPROCESSED_DIRNAME
    if not preprocessed_dir.exists():
        return []
    paths: list[Path] = []
    for run_dir in sorted(preprocessed_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        for filename in RECORD_FILENAMES:
            file_path = run_dir / filename
            if file_path.exists():
                paths.append(file_path)
    return paths


def _normalize_records(
    records: pd.DataFrame,
    *,
    join_id_column: str,
    text_source_column: str,
) -> pd.DataFrame:
    normalized = records.copy()
    normalized[join_id_column] = normalized[join_id_column].astype(str)
    if text_source_column != OUTPUT_TEXT_COLUMN:
        normalized[OUTPUT_TEXT_COLUMN] = normalized[text_source_column]
    return normalized.drop_duplicates(subset=[join_id_column], keep="first")


def load_preprocessed_records(dataset_dir: Path, platform: str) -> pd.DataFrame:
    """Load all preprocessed record rows for one dataset.

    Parameters
    ----------
    dataset_dir
        Dataset directory under a platform folder in the source data tree.
    platform
        Platform name (``bluesky``, ``twitter``, or ``reddit``).

    Returns
    -------
    pandas.DataFrame
        Combined preprocessed records for the dataset.

    Raises
    ------
    ValueError
        When ``platform`` is not a supported platform name.
    """
    join_id_column, text_source_column = _resolve_platform(platform)
    record_paths = _record_paths(dataset_dir)
    if not record_paths:
        return pd.DataFrame(columns=[join_id_column, OUTPUT_TEXT_COLUMN])

    frames = [read_table(path) for path in record_paths]
    combined = pd.concat(frames, ignore_index=True)
    return _normalize_records(
        combined,
        join_id_column=join_id_column,
        text_source_column=text_source_column,
    )


def _validate_label_columns(
    labels: pd.DataFrame,
    classifier_name: str,
    label_columns: tuple[str, ...],
) -> None:
    for column in label_columns:
        if column not in labels.columns:
            raise ValueError(
                f"Classifier {classifier_name} missing required column {column}"
            )


def _dedupe_labels(labels: pd.DataFrame) -> pd.DataFrame:
    sorted_labels = labels.sort_values(LABEL_TIMESTAMP_COLUMN, ascending=False)
    return sorted_labels.drop_duplicates(subset=[OUTPUT_ID_COLUMN], keep="first")


def _join_labels_to_records(
    labels: pd.DataFrame,
    records: pd.DataFrame,
    *,
    join_id_column: str,
) -> pd.DataFrame:
    deduped_labels = _dedupe_labels(labels)
    deduped_labels = deduped_labels.copy()
    deduped_labels[OUTPUT_ID_COLUMN] = deduped_labels[OUTPUT_ID_COLUMN].astype(str)

    normalized_records = records.copy()
    normalized_records[join_id_column] = normalized_records[join_id_column].astype(str)
    record_subset = normalized_records[[join_id_column, OUTPUT_TEXT_COLUMN]].rename(
        columns={join_id_column: OUTPUT_ID_COLUMN}
    )

    joined = deduped_labels.merge(record_subset, on=OUTPUT_ID_COLUMN, how="inner")
    return joined[joined[OUTPUT_TEXT_COLUMN].notna() & (joined[OUTPUT_TEXT_COLUMN] != "")]


def hydrate_classifier(
    labels: pd.DataFrame,
    records: pd.DataFrame,
    *,
    platform: str,
    classifier_name: str,
) -> pd.DataFrame:
    """Join labels to text and shape one classifier training table.

    Parameters
    ----------
    labels
        Classifier label rows for one dataset file.
    records
        Preprocessed record rows for the same dataset.
    platform
        Platform name used to resolve id and text columns.
    classifier_name
        Classifier whose label columns are retained on the output.

    Returns
    -------
    pandas.DataFrame
        Training rows with unified id, label time, text, and label columns.

    Raises
    ------
    ValueError
        When ``platform`` or ``classifier_name`` is unknown, or a required label
        column is missing from ``labels``.
    """
    join_id_column, _ = _resolve_platform(platform)
    label_columns = _resolve_classifier(classifier_name)
    output_columns = _output_columns(classifier_name)

    if labels.empty:
        return pd.DataFrame(columns=output_columns)

    _validate_label_columns(labels, classifier_name, label_columns)
    joined = _join_labels_to_records(
        labels,
        records,
        join_id_column=join_id_column,
    )
    return joined[output_columns].reset_index(drop=True)


def write_training_parquet(df: pd.DataFrame, path: Path) -> Path:
    """Write a training table to parquet.

    Parameters
    ----------
    df
        Training rows to persist.
    path
        Destination parquet path.

    Returns
    -------
    Path
        The written parquet path.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(path, index=False)
    return path
