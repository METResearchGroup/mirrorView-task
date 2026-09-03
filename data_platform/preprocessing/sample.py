"""Sample preprocessed rows before write.

Run from the repo root:

    PYTHONPATH=. uv run python -c \\
        "from data_platform.preprocessing.sample import sample_rows"
"""

from __future__ import annotations

from collections.abc import Iterator
from random import Random
from typing import TypeVar

import pandas as pd

MIN_SAMPLE_SIZE = 1
ONE_BASED_OFFSET = 1

T = TypeVar("T")


def _reservoir_sample(items: Iterator[T], sample_size: int, rng: Random) -> list[T]:
    sample: list[T] = []
    for item_number, item in enumerate(items, start=ONE_BASED_OFFSET):
        if item_number <= sample_size:
            sample.append(item)
            continue
        replacement_index = rng.randrange(item_number)
        if replacement_index < sample_size:
            sample[replacement_index] = item
    return sample


def sample_rows(
    records: pd.DataFrame,
    sample_size: int,
    sample_seed: int,
) -> pd.DataFrame:
    """Return a repeatable sample of preprocessed rows.

    Parameters
    ----------
    records
        Kept rows after preprocess filters.
    sample_size
        Maximum number of rows to keep. Must be at least 1.
    sample_seed
        Seed for Algorithm R.

    Returns
    -------
    pandas.DataFrame
        At most ``sample_size`` rows. If ``records`` is shorter, every row
        is returned.

    Raises
    ------
    ValueError
        When ``sample_size`` is less than 1.
    """
    if sample_size < MIN_SAMPLE_SIZE:
        raise ValueError("sample_size must be at least 1")
    if len(records) <= sample_size:
        return records
    sampled_rows = _reservoir_sample(
        iter(records.to_dict(orient="records")),
        sample_size,
        Random(sample_seed),
    )
    return pd.DataFrame(sampled_rows, columns=list(records.columns))
