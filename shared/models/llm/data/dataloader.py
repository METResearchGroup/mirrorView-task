"""Load Study 2 LoRA train and test splits from S3.

Each split is an object in ``mirrorview-experimental-artifacts``. The object
key is the repo-relative CSV path from ``shared.models.llm.data.registry``.

``load_split`` takes an upsampled dataset name and ``Split.TRAIN`` or
``Split.TEST``.
"""

from __future__ import annotations

from enum import StrEnum
from io import BytesIO

import pandas as pd

from shared.data.dataloader import _read_study_object
from shared.models.llm.data.registry import split_relative_path


class Split(StrEnum):
    """Train or test half of one upsampled Study 2 dataset."""

    TRAIN = "train"
    TEST = "test"


def load_split(dataset_name: str, split: Split | str, *, low_memory: bool = False) -> pd.DataFrame:
    """Load one registered train or test CSV from S3 with no transforms.

    Parameters
    ----------
    dataset_name
        ``UPSAMPLED_STUDY_2_KEEP_REMOVE_UNANIMOUS_LABELS``,
        ``UPSAMPLED_STUDY_2_KEEP_REMOVE_SPLIT_LABELS``, or
        ``UPSAMPLED_STUDY_2_KEEP_REMOVE_LABELS``.
    split
        ``Split.TRAIN`` or ``Split.TEST``. The strings ``"train"`` and
        ``"test"`` are accepted.

    Raises
    ------
    KeyError
        When ``dataset_name`` is not one of the three upsampled datasets.
    ValueError
        When ``split`` is not train or test.
    FileNotFoundError
        When the S3 object is missing.
    """
    parsed = _require_split(split)
    key = split_relative_path(dataset_name, parsed.value).as_posix()
    body = _read_study_object(key)
    return pd.read_csv(BytesIO(body), low_memory=low_memory)


def _require_split(split: Split | str) -> Split:
    """Return ``split`` as a ``Split`` member.

    Raises
    ------
    ValueError
        When ``split`` is not train or test.
    """
    if isinstance(split, Split):
        return split
    try:
        return Split(split)
    except ValueError as exc:
        valid = ", ".join(member.value for member in Split)
        raise ValueError(f"Unknown split {split!r}. Valid splits: {valid}") from exc
