"""Walk the source data tree and build per-classifier training parquets."""

from pathlib import Path


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
        Paths of every parquet written during the run.
    """
    raise NotImplementedError
