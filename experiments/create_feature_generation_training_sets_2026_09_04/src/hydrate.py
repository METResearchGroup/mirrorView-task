"""Join classifier labels to preprocessed records and write training parquets."""

from pathlib import Path

import pandas as pd


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
    raise NotImplementedError


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
    """
    raise NotImplementedError


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
    """
    raise NotImplementedError


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
    raise NotImplementedError
