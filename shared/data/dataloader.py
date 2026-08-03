"""Loader for datasets registered in ``shared.data.registry``.

Resolves any registered name (raw or transformed) to its CSV path and reads it
with no further transforms.
"""

from __future__ import annotations

import pandas as pd

from shared.data import registry


def load_dataset(name: str, *, low_memory: bool = False) -> pd.DataFrame:
    """Load a registered study CSV by name with no transforms.

    Works for raw and transformed registry entries alike.

    Raises:
        KeyError: If ``name`` is not in the registry.
        FileNotFoundError: If the resolved CSV path is missing on disk.
    """
    path = registry.resolve_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset file not found: {path}")
    return pd.read_csv(path, low_memory=low_memory)
