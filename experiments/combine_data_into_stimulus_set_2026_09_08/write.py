"""Write the combined parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    CombineRunResult,
    DATASET_FILENAME,
    OUTPUT_S3_BUCKET,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "combine_data_into_stimulus_set_2026_09_08"
)


def write_local_parquet(combined: pd.DataFrame, experiment_dir: Path) -> tuple[Path, bytes]:
    """Write ``dataset.parquet`` under the experiment folder and return its bytes.

    Parameters
    ----------
    combined
        Sorted 17-column stimulus table.
    experiment_dir
        Folder that receives ``dataset.parquet``.

    Returns
    -------
    tuple[Path, bytes]
        Local path and parquet bytes.
    """
    body = _parquet_bytes(combined)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return path, body


def write_combined_dataset(
    combined: pd.DataFrame,
    overall_crosstab: dict[str, dict[str, int]],
    integration_crosstab: dict[str, dict[str, dict[str, int]]],
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> CombineRunResult:
    """Write local parquet, upload to S3, and write RESULTS.md.

    Parameters
    ----------
    combined
        Sorted 17-column stimulus table.
    overall_crosstab
        Stance by toxicity counts across all rows.
    integration_crosstab
        Stance by toxicity counts keyed by platform.
    experiment_dir
        Folder that receives ``dataset.parquet`` and ``RESULTS.md``.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    CombineRunResult
        Local path, S3 URI, SHA-256, and the two count tables.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    raise NotImplementedError


def print_run_summary(result: CombineRunResult) -> None:
    """Print combined row count, URIs, SHA-256, and both crosstab tables."""
    raise NotImplementedError


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
