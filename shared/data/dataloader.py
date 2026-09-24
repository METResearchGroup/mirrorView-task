"""Loader for datasets registered in ``shared.data.registry``.

File-backed names resolve to a CSV path and are read with no further
transforms. Union names stack their source datasets.
"""

from __future__ import annotations

import pandas as pd

from shared.data import registry
from shared.data.union import concat_frames, union_stimuli_frames


def load_dataset(name: str, *, low_memory: bool = False) -> pd.DataFrame:
    """Load a registered study table by name.

    File-backed entries are read as CSV with no transforms. Union entries
    stack their source tables. Stimuli unions keep one row per
    ``post_primary_key``.

    Raises:
        KeyError: If ``name`` is not in the registry.
        FileNotFoundError: If a file-backed CSV path is missing on disk.
        ValueError: If a union has no source frames.
    """
    entry = registry.get_dataset(name)
    if entry.is_union:
        return _load_union_dataset(entry, low_memory=low_memory)
    path = registry.resolve_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    return pd.read_csv(path, low_memory=low_memory)


def _load_union_dataset(
    entry: registry.DatasetEntry, *, low_memory: bool
) -> pd.DataFrame:
    frames = [
        load_dataset(source_name, low_memory=low_memory)
        for source_name in entry.source_names
    ]
    if entry.kind == "stimuli":
        return union_stimuli_frames(frames)
    return concat_frames(frames)
