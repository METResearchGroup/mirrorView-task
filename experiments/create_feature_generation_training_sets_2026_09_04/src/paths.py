"""Path helpers for the feature-generation training-set experiment."""

from pathlib import Path


def experiment_root() -> Path:
    """Return the experiment package root directory."""
    return Path(__file__).resolve().parent.parent


def training_data_root() -> Path:
    """Return the local directory that holds per-classifier training parquets."""
    return experiment_root() / "training_data"


def category_dir(classifier_name: str) -> Path:
    """Return the output directory for one classifier's training parquets.

    Parameters
    ----------
    classifier_name
        One of the locked classifier folder names.

    Returns
    -------
    Path
        ``training_data/{classifier_name}``.
    """
    return training_data_root() / classifier_name


def output_parquet_path(
    classifier_name: str,
    dataset_id: str,
    timestamp: str,
) -> Path:
    """Build the local parquet path for one dataset and classifier.

    Parameters
    ----------
    classifier_name
        Classifier folder name under ``training_data/``.
    dataset_id
        Platform dataset identifier.
    timestamp
        UTC run timestamp from ``get_current_timestamp``.

    Returns
    -------
    Path
        ``training_data/{classifier_name}/{dataset_id}_{timestamp}.parquet``.
    """
    filename = f"{dataset_id}_{timestamp}.parquet"
    return training_data_root() / classifier_name / filename
