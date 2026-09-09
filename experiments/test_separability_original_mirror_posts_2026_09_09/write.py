"""Upload the shared presentation parquet to S3.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/test_separability_original_mirror_posts_2026_09_09/run.py --help
"""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.test_separability_original_mirror_posts_2026_09_09.constants import (
    OUTPUT_S3_BUCKET,
    OUTPUTS_DIRNAME,
    PRESENTATION_COLUMNS,
    PRESENTATION_FILENAME,
    PRESENTATION_S3_KEY,
    PresentationWriteResult,
    SHA256_PRINT_FORMAT,
    WROTE_PRESENTATIONS_FORMAT,
)
from lib.constants import REPO_ROOT


def require_presentation_key_absent(store: CampaignObjectStore) -> None:
    """Raise FileExistsError when the presentation S3 key already exists.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    if store.get(PRESENTATION_S3_KEY) is not None:
        raise FileExistsError(
            f"Object already exists: {s3_uri(OUTPUT_S3_BUCKET, PRESENTATION_S3_KEY)}"
        )


def upload_presentation(
    presentations: pd.DataFrame,
    experiment_dir: Path,
    store: CampaignObjectStore,
) -> PresentationWriteResult:
    """Write local parquet, upload with put_new, and return the digest.

    Parameters
    ----------
    presentations
        Presentation rows in contract column order.
    experiment_dir
        Experiment folder that receives a local copy.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    PresentationWriteResult
        Row count, URIs, and SHA-256.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    body = _parquet_bytes(presentations)
    local_path = _write_local_parquet(body, experiment_dir)
    store.put_new(PRESENTATION_S3_KEY, body)
    digest = sha256_hex(body)
    return PresentationWriteResult(
        row_count=len(presentations),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, PRESENTATION_S3_KEY),
        sha256=digest,
        local_path=str(local_path.relative_to(REPO_ROOT)),
    )


def print_presentation_summary(result: PresentationWriteResult) -> None:
    """Print the presentation row count and SHA-256.

    Parameters
    ----------
    result
        Upload result from ``upload_presentation``.
    """
    print(WROTE_PRESENTATIONS_FORMAT.format(row_count=result.row_count))
    print(SHA256_PRINT_FORMAT.format(digest=result.sha256))


def _write_local_parquet(body: bytes, experiment_dir: Path) -> Path:
    output_dir = experiment_dir / OUTPUTS_DIRNAME
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / PRESENTATION_FILENAME
    path.write_bytes(body)
    return path


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    ordered = frame.loc[:, list(PRESENTATION_COLUMNS)]
    buffer = io.BytesIO()
    ordered.to_parquet(buffer, index=False)
    return buffer.getvalue()
