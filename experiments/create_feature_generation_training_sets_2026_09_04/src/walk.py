"""Walk the source data tree and build per-classifier training parquets."""

from pathlib import Path

import pandas as pd

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    CLASSIFIER_NAMES,
    PLATFORMS,
)
from experiments.create_feature_generation_training_sets_2026_09_04.src.hydrate import (
    hydrate_classifier,
    load_preprocessed_records,
    read_table,
    write_training_parquet,
)

FEATURES_DIRNAME = "features"


def _classifier_csv_path(dataset_dir: Path, classifier_name: str) -> Path:
    return dataset_dir / FEATURES_DIRNAME / f"{classifier_name}.csv"


def _output_parquet_path(
    output_root: Path,
    classifier_name: str,
    dataset_id: str,
    timestamp: str,
) -> Path:
    filename = f"{dataset_id}_{timestamp}.parquet"
    return output_root / classifier_name / filename


def _dataset_has_classifier_files(dataset_dir: Path) -> bool:
    return any(
        _classifier_csv_path(dataset_dir, classifier_name).exists()
        for classifier_name in CLASSIFIER_NAMES
    )


def _write_classifier_parquet(
    *,
    dataset_dir: Path,
    dataset_id: str,
    platform: str,
    classifier_name: str,
    records: pd.DataFrame,
    timestamp: str,
    output_root: Path,
) -> Path:
    classifier_path = _classifier_csv_path(dataset_dir, classifier_name)
    labels = read_table(classifier_path)
    training_frame = hydrate_classifier(
        labels,
        records,
        platform=platform,
        classifier_name=classifier_name,
    )
    if training_frame.empty:
        print(
            f"warning: {dataset_id} classifier {classifier_name} produced zero rows"
        )

    output_path = _output_parquet_path(
        output_root,
        classifier_name,
        dataset_id,
        timestamp,
    )
    write_training_parquet(training_frame, output_path)
    print(output_path)
    return output_path


def _process_dataset(
    *,
    dataset_dir: Path,
    dataset_id: str,
    platform: str,
    timestamp: str,
    output_root: Path,
) -> list[Path]:
    if not _dataset_has_classifier_files(dataset_dir):
        return []

    records = load_preprocessed_records(dataset_dir, platform)
    written_paths: list[Path] = []

    for classifier_name in CLASSIFIER_NAMES:
        classifier_path = _classifier_csv_path(dataset_dir, classifier_name)
        if not classifier_path.exists():
            print(f"skipping {dataset_id}: missing classifier {classifier_name}")
            continue

        written_paths.append(
            _write_classifier_parquet(
                dataset_dir=dataset_dir,
                dataset_id=dataset_id,
                platform=platform,
                classifier_name=classifier_name,
                records=records,
                timestamp=timestamp,
                output_root=output_root,
            )
        )

    return written_paths


def build_training_sets(
    data_root: Path,
    *,
    timestamp: str,
    output_root: Path,
) -> list[Path]:
    """Build training parquets for every existing classifier file under ``data_root``.

    Parameters
    ----------
    data_root
        Root of the platform dataset tree on disk.
    timestamp
        UTC run timestamp stamped on every output parquet filename.
    output_root
        Local root directory for per-classifier training outputs.

    Returns
    -------
    list[Path]
        Paths of every parquet written during the run, sorted.
    """
    written_paths: list[Path] = []

    for platform in PLATFORMS:
        platform_dir = data_root / platform
        if not platform_dir.is_dir():
            continue

        for dataset_entry in sorted(platform_dir.iterdir()):
            if not dataset_entry.is_dir():
                continue

            written_paths.extend(
                _process_dataset(
                    dataset_dir=dataset_entry,
                    dataset_id=dataset_entry.name,
                    platform=platform,
                    timestamp=timestamp,
                    output_root=output_root,
                )
            )

    written_paths.sort()
    print(f"wrote {len(written_paths)} parquets")
    return written_paths
