"""Write remaining label counts locally, upload to S3, and write RESULTS.md.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import sha256_hex
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.constants import (
    CSV_INDEX,
    DATASET_FILENAME,
    LabelCountRunResult,
    LocalCsvWrite,
    NewSampleSource,
    OUTPUT_COLUMNS,
    OUTPUT_S3_KEY,
)

CSV_ENCODING = "utf-8"


def write_local_csv(counts: pd.DataFrame, experiment_dir: Path) -> LocalCsvWrite:
    """Write the remaining-label CSV under the experiment folder.

    Parameters
    ----------
    counts
        Remaining-label table.
    experiment_dir
        Folder that receives the CSV.

    Returns
    -------
    LocalCsvWrite
        Local path and CSV bytes.
    """
    body = _csv_bytes(counts)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return LocalCsvWrite(path=path, body=body)


def upload_csv(body: bytes, store: CampaignObjectStore) -> str:
    """Upload CSV bytes only if the S3 key does not already exist.

    Parameters
    ----------
    body
        CSV bytes already written locally.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    str
        SHA-256 of the uploaded bytes.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    store.put_new(OUTPUT_S3_KEY, body)
    return sha256_hex(body)


def write_results_md(result: LabelCountRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with remaining-label totals.

    Parameters
    ----------
    result
        Counts and paths from the run.
    experiment_dir
        Folder that receives ``RESULTS.md``.

    Returns
    -------
    Path
        Path of the written report.
    """
    raise NotImplementedError


def write_required_label_counts(
    counts: pd.DataFrame,
    source: NewSampleSource,
    experiment_dir: Path,
    store: CampaignObjectStore,
    old_catalog_ids: int,
) -> LabelCountRunResult:
    """Write the local CSV, upload it, and write RESULTS.md.

    Parameters
    ----------
    counts
        Remaining-label table.
    source
        Pinned new sample identity recorded in RESULTS.md.
    experiment_dir
        Folder that receives the CSV and RESULTS.md.
    store
        Object store used only with ``put_new``.
    old_catalog_ids
        Unique id count in the old catalog before dropping completed posts.

    Returns
    -------
    LabelCountRunResult
        Counts, local path, S3 URI, and SHA-256.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    raise NotImplementedError


def print_run_summary(result: LabelCountRunResult) -> None:
    """Print remaining label totals and the S3 URI."""
    raise NotImplementedError


def _csv_bytes(counts: pd.DataFrame) -> bytes:
    ordered = counts.loc[:, list(OUTPUT_COLUMNS)]
    return ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
