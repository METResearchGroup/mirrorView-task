"""Reservoir-sample dump comments without loading the full stream."""

from __future__ import annotations

from collections.abc import Iterator
from random import Random
from typing import TypeVar

T = TypeVar("T")

DEFAULT_SAMPLE_SIZE = 500_000
DEFAULT_SAMPLE_SEED = 20260615
MIN_SAMPLE_SIZE = 1
ONE_BASED_OFFSET = 1


def reservoir_sample(items: Iterator[T], sample_size: int, rng: Random) -> list[T]:
    """Return up to ``sample_size`` items chosen uniformly from a stream.

    Parameters
    ----------
    items
        Stream of values. Consumed once.
    sample_size
        Maximum number of items to keep. Must be at least 1.
    rng
        Random generator used for replacement draws.

    Returns
    -------
    list[T]
        Sampled items. If the stream is shorter than ``sample_size``, every
        item is returned in stream order.

    Raises
    ------
    ValueError
        When ``sample_size`` is less than 1.
    """
    if sample_size < MIN_SAMPLE_SIZE:
        raise ValueError("sample_size must be at least 1")

    sample: list[T] = []
    for item_number, item in enumerate(items, start=ONE_BASED_OFFSET):
        if item_number <= sample_size:
            sample.append(item)
            continue
        replacement_index = rng.randrange(item_number)
        if replacement_index < sample_size:
            sample[replacement_index] = item
    return sample
