"""Catalog of Study 2 LoRA train and test CSV objects.

Each object lives in ``mirrorview-experimental-artifacts``. The object key is
the repo-relative path under ``shared/models/llm/data/``.
"""

from __future__ import annotations

from pathlib import Path

from shared.data.registry import (
    REPO_ROOT,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
)

DATA_ROOT = Path("shared/models/llm/data")

SOURCE_DATASETS: tuple[str, ...] = (
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS,
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS,
)

OUTPUT_DIRECTORIES: dict[str, str] = {
    UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS: (
        "upsampled_study_2_keep_remove_unanimous_labels"
    ),
    UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS: (
        "upsampled_study_2_keep_remove_split_labels"
    ),
    UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS: "upsampled_study_2_keep_remove_labels",
}

SPLIT_NAMES: frozenset[str] = frozenset({"train", "test"})


def output_directory(dataset_name: str) -> str:
    """Return the folder name for one upsampled Study 2 dataset.

    Raises
    ------
    KeyError
        When ``dataset_name`` is not one of the three upsampled datasets.
    """
    try:
        return OUTPUT_DIRECTORIES[dataset_name]
    except KeyError as exc:
        known = ", ".join(SOURCE_DATASETS)
        raise KeyError(
            f"Unknown dataset {dataset_name!r}. Valid names are: {known}"
        ) from exc


def split_relative_path(dataset_name: str, split_name: str) -> Path:
    """Repo-relative CSV path for one dataset and one split.

    Raises
    ------
    KeyError
        When ``dataset_name`` is not one of the three upsampled datasets.
    ValueError
        When ``split_name`` is not ``train`` or ``test``.
    """
    if split_name not in SPLIT_NAMES:
        valid = ", ".join(sorted(SPLIT_NAMES))
        raise ValueError(f"Unknown split {split_name!r}. Valid splits: {valid}")
    return DATA_ROOT / output_directory(dataset_name) / f"{split_name}.csv"


def resolve_split_path(dataset_name: str, split_name: str, *, root: Path | None = None) -> Path:
    """Absolute CSV path for one dataset and one split.

    Parameters
    ----------
    root
        Directory that contains ``shared/``. Defaults to the repository root.
        Does not check that the file exists.
    """
    base = REPO_ROOT if root is None else root
    return base / split_relative_path(dataset_name, split_name)
