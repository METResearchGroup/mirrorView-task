"""S3 key helpers for flip-generation artifacts."""

from __future__ import annotations

BATCHES_DIRNAME = "batches"
PART_FILENAME_TEMPLATE = "part-{part_index:05d}.parquet"
ERRORS_FILENAME = "errors.jsonl"
FINAL_FILENAME = "flips.parquet"


def _validate_run_prefix(run_prefix: str) -> None:
    if not run_prefix.endswith("/"):
        raise ValueError(f"run_prefix must end with '/': {run_prefix!r}")


def part_key(run_prefix: str, part_index: int) -> str:
    """Return the S3 key for one batch part.

    Parameters
    ----------
    run_prefix
        Key prefix ending in ``/``.
    part_index
        Zero-based batch index.

    Returns
    -------
    str
        Full object key for the part parquet.

    Raises
    ------
    ValueError
        When ``run_prefix`` does not end with ``/`` or ``part_index`` is negative.
    """
    _validate_run_prefix(run_prefix)
    if part_index < 0:
        raise ValueError(f"part_index must be non-negative: {part_index}")
    raise NotImplementedError


def errors_key(run_prefix: str) -> str:
    """Return the S3 key for the append-only errors log.

    Raises
    ------
    ValueError
        When ``run_prefix`` does not end with ``/``.
    """
    _validate_run_prefix(run_prefix)
    raise NotImplementedError


def final_key(run_prefix: str) -> str:
    """Return the S3 key for the concatenated flips parquet.

    Raises
    ------
    ValueError
        When ``run_prefix`` does not end with ``/``.
    """
    _validate_run_prefix(run_prefix)
    raise NotImplementedError
