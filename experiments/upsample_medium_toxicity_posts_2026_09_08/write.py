"""Write the unused medium parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

import io
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    DATASET_FILENAME,
    EXPERIMENT_DIR,
    LEFT_STANCE,
    LeftoverMediumSample,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    RESULTS_FILENAME,
    RIGHT_STANCE,
    STANCE_COLUMN,
    UpsampleRunResult,
)
from lib.constants import REPO_ROOT

RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py"""


def write_upsampled_dataset(
    leftover: LeftoverMediumSample,
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> UpsampleRunResult:
    """Write local parquet, upload to S3, and write RESULTS.md.

    Parameters
    ----------
    leftover
        Sampled unused medium table plus leftover cell counts.
    experiment_dir
        Folder that receives the parquet and RESULTS.md.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    UpsampleRunResult
        Local path, S3 URI, SHA-256, and counts.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    resolved_store = store if store is not None else _default_store()
    local_path, body = write_local_parquet(leftover.sampled, resolved_dir)
    digest = upload_dataset(body, resolved_store)
    result = _upsample_run_result(leftover, local_path, digest)
    write_results_md(result, resolved_dir)
    return result


def write_local_parquet(
    sampled: pd.DataFrame, experiment_dir: Path
) -> tuple[Path, bytes]:
    """Write the upsample parquet under the experiment folder.

    Parameters
    ----------
    sampled
        Sorted unused medium table.
    experiment_dir
        Folder that receives the parquet.

    Returns
    -------
    tuple[Path, bytes]
        Local path and parquet bytes.
    """
    body = _parquet_bytes(sampled)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return path, body


def upload_dataset(body: bytes, store: CampaignObjectStore) -> str:
    """Upload parquet bytes with put_new and return the SHA-256.

    Parameters
    ----------
    body
        Parquet bytes already written locally.
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


def write_results_md(result: UpsampleRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with leftover counts, URIs, and SHA-256."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def print_run_summary(result: UpsampleRunResult) -> None:
    """Print row counts, leftover counts, S3 URI, and SHA-256."""
    print(f"sampled_rows={result.sampled_rows}")
    print(f"left_medium={result.left_medium}")
    print(f"right_medium={result.right_medium}")
    print(f"leftover_left_medium={result.leftover_left_medium}")
    print(f"right_medium_leftover_before_sample={result.leftover_right_medium}")
    print(f"local_path={result.local_path}")
    print(f"s3_uri={result.s3_uri}")
    print(f"dataset_sha256={result.dataset_sha256}")


def _upsample_run_result(
    leftover: LeftoverMediumSample,
    local_path: Path,
    digest: str,
) -> UpsampleRunResult:
    sampled = leftover.sampled
    return UpsampleRunResult(
        sampled_rows=len(sampled),
        left_medium=_stance_count(sampled, LEFT_STANCE),
        right_medium=_stance_count(sampled, RIGHT_STANCE),
        leftover_left_medium=leftover.leftover_left_medium,
        leftover_right_medium=leftover.leftover_right_medium,
        local_path=str(local_path.relative_to(REPO_ROOT)),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        dataset_sha256=digest,
    )


def _stance_count(frame: pd.DataFrame, stance: str) -> int:
    return int((frame[STANCE_COLUMN] == stance).sum())


def _results_markdown(result: UpsampleRunResult) -> str:
    return "\n".join(
        [
            *_results_preamble(result),
            "## Sampled unused medium posts",
            "",
            _counts_table_markdown(result),
            "",
        ]
    )


def _results_preamble(result: UpsampleRunResult) -> list[str]:
    return [
        "# Upsample unused medium toxicity posts, results",
        "",
        "## Command",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Upsampled parquet",
        "",
        _parquet_table_markdown(result),
        "",
    ]


def _parquet_table_markdown(result: UpsampleRunResult) -> str:
    return "\n".join(
        [
            "| File | Path | SHA-256 |",
            "| ---- | ---- | ------- |",
            f"| Local parquet | `{result.local_path}` | `{result.dataset_sha256}` |",
            f"| S3 parquet | `{result.s3_uri}` | `{result.dataset_sha256}` |",
        ]
    )


def _counts_table_markdown(result: UpsampleRunResult) -> str:
    return "\n".join(
        [
            "| Field | Count |",
            "| ----- | ----: |",
            f"| Sampled rows | {result.sampled_rows} |",
            f"| Left medium | {result.left_medium} |",
            f"| Right medium | {result.right_medium} |",
            f"| Leftover left medium before sample | {result.leftover_left_medium} |",
            f"| Leftover right medium before sample | {result.leftover_right_medium} |",
        ]
    )


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
