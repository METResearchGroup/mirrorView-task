"""Experiment paths, keep/remove loader, and class-split helpers.

Run from repo root::

    PYTHONPATH=. uv run python -c "
    from experiments.create_llm_features_2026_08_05.src import paths
    df = paths.load_keep_remove_posts()
    keep_df, remove_df = paths.split_by_decision(df)
    print(len(df), len(keep_df), len(remove_df))
    "
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

import pandas as pd

from shared.data.dataloader import load_dataset
from shared.data.registry import STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS

EXPERIMENT_ROOT = Path(__file__).resolve().parents[1]
REQUIRED_COLUMNS = ("message_id", "original_text", "mirror_text", "decision")
VALID_DECISIONS = frozenset({"keep", "remove"})


class LabelClass(str, Enum):
    """Allowed keep/remove class labels for stage output paths."""

    KEEP = "keep"
    REMOVE = "remove"


def validate_label_class(label_class: str) -> LabelClass:
    """Return the LabelClass enum for a string label class.

    Parameters
    ----------
    label_class
        Must be exactly ``keep`` or ``remove``.

    Returns
    -------
    LabelClass
        Parsed enum value.

    Raises
    ------
    ValueError
        When ``label_class`` is not keep or remove.
    """
    try:
        return LabelClass(label_class)
    except ValueError as exc:
        raise ValueError(
            f"label_class must be 'keep' or 'remove', got {label_class!r}"
        ) from exc


def stage1_root(label_class: str) -> Path:
    """Return Stage-1 generated-features root for one label class."""
    cls = validate_label_class(label_class)
    return EXPERIMENT_ROOT / "outputs" / "generated_features" / cls.value


def stage2_root(label_class: str) -> Path:
    """Return Stage-2 generated-embeddings root for one label class."""
    cls = validate_label_class(label_class)
    return EXPERIMENT_ROOT / "outputs" / "generated_embeddings" / cls.value


def stage3_root(label_class: str) -> Path:
    """Return Stage-3 clusters root for one label class."""
    cls = validate_label_class(label_class)
    return EXPERIMENT_ROOT / "outputs" / "clusters" / cls.value


def stage4_root(label_class: str) -> Path:
    """Return Stage-4 generated-labels root for one label class."""
    cls = validate_label_class(label_class)
    return EXPERIMENT_ROOT / "outputs" / "generated_labels" / cls.value


def _normalize_decision_column(frame: pd.DataFrame) -> pd.DataFrame:
    """Return a copy with lowercase stripped decision values."""
    out = frame.copy()
    out["decision"] = out["decision"].astype(str).str.strip().str.lower()
    return out


def _assert_required_columns(frame: pd.DataFrame) -> None:
    """Raise KeyError when required columns are missing."""
    missing = set(REQUIRED_COLUMNS) - set(frame.columns)
    if missing:
        raise KeyError(f"Keep/remove labels missing columns: {sorted(missing)}")


def _assert_valid_decisions(frame: pd.DataFrame) -> None:
    """Raise ValueError when decision values are outside keep/remove."""
    observed = set(frame["decision"].unique())
    if not observed <= VALID_DECISIONS:
        raise ValueError(
            f"decision values must be subset of {sorted(VALID_DECISIONS)}, "
            f"got {sorted(observed)}"
        )


def load_keep_remove_posts() -> pd.DataFrame:
    """Load modal Study Phase 2 Part 2 keep/remove labels.

    Returns
    -------
    pd.DataFrame
        One row per post with required columns and normalized decisions.
    """
    frame = load_dataset(STUDY_PHASE_2_PART_2_KEEP_REMOVE_LABELS, low_memory=False)
    _assert_required_columns(frame)
    normalized = _normalize_decision_column(frame[list(REQUIRED_COLUMNS)])
    _assert_valid_decisions(normalized)
    return normalized.reset_index(drop=True)


def split_by_decision(df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a keep/remove frame into (keep_df, remove_df).

    Parameters
    ----------
    df
        Frame with a ``decision`` column of keep/remove values.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        Keep rows then remove rows.
    """
    _assert_required_columns(df)
    normalized = _normalize_decision_column(df)
    _assert_valid_decisions(normalized)
    keep_df = normalized[normalized["decision"] == LabelClass.KEEP.value].reset_index(
        drop=True
    )
    remove_df = normalized[
        normalized["decision"] == LabelClass.REMOVE.value
    ].reset_index(drop=True)
    return keep_df, remove_df


def latest_timestamp_subdir(parent: Path) -> Path:
    """Return the newest child directory under ``parent``.

    Parameters
    ----------
    parent
        Directory that contains timestamped run folders.

    Returns
    -------
    Path
        Latest child directory by name sort.

    Raises
    ------
    FileNotFoundError
        When parent is missing or has no child directories.
    """
    if not parent.is_dir():
        raise FileNotFoundError(f"Directory not found: {parent}")
    children = [path for path in parent.iterdir() if path.is_dir()]
    if not children:
        raise FileNotFoundError(f"No timestamp subdirectories under {parent}")
    return sorted(children, key=lambda path: path.name)[-1]
