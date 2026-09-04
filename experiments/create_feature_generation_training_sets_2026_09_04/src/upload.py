"""Upload training parquets to the locked S3 bucket and prefix.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/create_feature_generation_training_sets_2026_09_04/main.py --upload
"""

from __future__ import annotations

from pathlib import Path

from lib.aws.s3 import S3

from experiments.create_feature_generation_training_sets_2026_09_04.src.constants import (
    S3_BUCKET,
    S3_PREFIX,
)

GITKEEP_FILENAME = ".gitkeep"


def s3_key_for(local_path: Path, output_root: Path) -> str:
    """Build the S3 object key for one local training parquet.

    Parameters
    ----------
    local_path
        Path to a parquet under ``output_root``.
    output_root
        Local root that holds per-classifier training outputs.

    Returns
    -------
    str
        ``{S3_PREFIX}/{relative posix path}``.
    """
    relative_path = local_path.relative_to(output_root).as_posix()
    return f"{S3_PREFIX}/{relative_path}"


def upload_training_parquets(
    paths: list[Path],
    output_root: Path,
    s3_client: S3 | None = None,
) -> list[str]:
    """Upload training parquets to S3 and return their object keys.

    Parameters
    ----------
    paths
        Local parquet paths produced by :func:`build_training_sets`.
    output_root
        Local root used to compute each object's relative key.
    s3_client
        Optional S3 client for tests; defaults to :class:`S3` on ``S3_BUCKET``.

    Returns
    -------
    list[str]
        Uploaded object keys in the same order as ``paths``, skipping ``.gitkeep``.
    """
    client = s3_client if s3_client is not None else S3(S3_BUCKET)
    uploaded_keys: list[str] = []

    for local_path in paths:
        if local_path.name == GITKEEP_FILENAME:
            continue

        object_key = s3_key_for(local_path, output_root)
        client.upload_file(local_path, object_key)
        uploaded_keys.append(object_key)

    return uploaded_keys
