"""Write the sampled parquet locally, upload it to S3, and write RESULTS.md."""

from __future__ import annotations

import io
import json
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.combine_data_into_stimulus_set_2026_09_08.crosstab import (
    stance_by_toxicity,
    stance_by_toxicity_by_integration,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    CANDIDATE_SHA256,
    CANDIDATE_S3_URI,
    CANDIDATE_STANCE_ROWS,
    CANDIDATE_TOXICITY_COLUMNS,
    CleanupSummary,
    DATASET_FILENAME,
    FilterRunResult,
    HIGH_TOXICITY,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    RESULTS_FILENAME,
    RIGHT_STANCE,
    STANCE_COLUMN,
    TARGET_PER_CELL,
    TARGET_TOTAL,
    TOXICITY_COLUMN,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "filter_posts_used_for_stimulus_dataset_2026_09_08"
)
JSON_INDENT = 2
TOTAL_LABEL = "total"
RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py"""


def write_local_parquet(sampled: pd.DataFrame, experiment_dir: Path) -> tuple[Path, bytes]:
    """Write ``dataset.parquet`` under the experiment folder and return its bytes.

    Parameters
    ----------
    sampled
        Sorted sampled stimulus table.
    experiment_dir
        Folder that receives ``dataset.parquet``.

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


def write_filtered_dataset(
    sampled: pd.DataFrame,
    cleaned: pd.DataFrame,
    summary: CleanupSummary,
    experiment_dir: Path | None = None,
    store: CampaignObjectStore | None = None,
) -> FilterRunResult:
    """Write local parquet, upload to S3, and write RESULTS.md.

    Parameters
    ----------
    sampled
        Sampled 17-column stimulus table.
    cleaned
        Cleaned table before sampling.
    summary
        Drop counts from cleanup.
    experiment_dir
        Folder that receives ``dataset.parquet`` and ``RESULTS.md``.
    store
        Object store used only with ``put_new``.

    Returns
    -------
    FilterRunResult
        Local path, S3 URI, SHA-256, and count tables.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    resolved_store = store if store is not None else _default_store()
    local_path, body = write_local_parquet(sampled, resolved_dir)
    digest = upload_dataset(body, resolved_store)
    result = _filter_run_result(sampled, cleaned, summary, local_path, digest)
    write_results_md(result, resolved_dir)
    return result


def print_run_summary(result: FilterRunResult) -> None:
    """Print row counts, URIs, SHA-256, and both crosstab tables."""
    print(f"candidate_rows={result.candidate_rows}")
    print(f"cleaned_rows={result.cleaned_rows}")
    print(f"sampled_rows={result.sampled_rows}")
    print(f"right_high_available={result.right_high_available}")
    print(f"right_high_shortfall={result.right_high_shortfall}")
    print(f"local_path={result.local_path}")
    print(f"s3_uri={result.s3_uri}")
    print(f"dataset_sha256={result.dataset_sha256}")
    print("cleaned_crosstab=")
    print(json.dumps(result.cleaned_crosstab, indent=JSON_INDENT))
    print("sampled_crosstab=")
    print(json.dumps(result.sampled_crosstab, indent=JSON_INDENT))


def write_results_md(result: FilterRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with cleanup counts, URIs, and both crosstab tables."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def _filter_run_result(
    sampled: pd.DataFrame,
    cleaned: pd.DataFrame,
    summary: CleanupSummary,
    local_path: Path,
    digest: str,
) -> FilterRunResult:
    right_high_available = _right_high_count(cleaned)
    return FilterRunResult(
        candidate_rows=summary.candidate_rows,
        cleaned_rows=summary.cleaned_rows,
        sampled_rows=len(sampled),
        right_high_available=right_high_available,
        right_high_shortfall=max(0, TARGET_PER_CELL - right_high_available),
        local_path=str(local_path.relative_to(REPO_ROOT)),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        dataset_sha256=digest,
        cleanup_summary=summary,
        cleaned_crosstab=stance_by_toxicity(cleaned),
        sampled_crosstab=stance_by_toxicity(sampled),
        sampled_integration_crosstab=stance_by_toxicity_by_integration(sampled),
    )


def _right_high_count(frame: pd.DataFrame) -> int:
    mask = (frame[STANCE_COLUMN] == RIGHT_STANCE) & (
        frame[TOXICITY_COLUMN] == HIGH_TOXICITY
    )
    return int(mask.sum())


def _results_markdown(result: FilterRunResult) -> str:
    return "\n".join(
        [
            *_results_preamble(result),
            "## Cleaned political stance by LLM toxicity tier",
            "",
            _stance_table_markdown(result.cleaned_crosstab),
            "",
            "## Sampled political stance by LLM toxicity tier",
            "",
            _stance_table_markdown(result.sampled_crosstab),
            "",
            _right_high_sentence(result),
            "",
        ]
    )


def _results_preamble(result: FilterRunResult) -> list[str]:
    return [
        "# Filter posts used for stimulus dataset, results",
        "",
        "## Command",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Candidate source",
        "",
        (
            f"Object `{CANDIDATE_S3_URI}` SHA-256 `{CANDIDATE_SHA256}` "
            f"has {result.candidate_rows} rows."
        ),
        "",
        "## Cleanup",
        "",
        _cleanup_table_markdown(result.cleanup_summary),
        "",
        "## Filtered parquet",
        "",
        _parquet_table_markdown(result),
        "",
        f"Sampled row count is {result.sampled_rows}. Aimed total is {TARGET_TOTAL}.",
        "",
    ]


def _cleanup_table_markdown(summary: CleanupSummary) -> str:
    return "\n".join(
        [
            "| Step | Rows dropped | Rows remaining |",
            "| ---- | -----------: | -------------: |",
            f"| Start | 0 | {summary.candidate_rows} |",
            (
                f"| Previously used record ids | {summary.dropped_previous_ids} | "
                f"{summary.candidate_rows - summary.dropped_previous_ids} |"
            ),
            (
                f"| Previously used original text | {summary.dropped_previous_text} | "
                f"{_after_previous_text(summary)} |"
            ),
            (
                f"| Duplicate record ids | {summary.dropped_duplicate_ids} | "
                f"{_after_duplicate_ids(summary)} |"
            ),
            (
                f"| Duplicate text | {summary.dropped_duplicate_text} | "
                f"{summary.cleaned_rows} |"
            ),
        ]
    )


def _after_previous_text(summary: CleanupSummary) -> int:
    return (
        summary.candidate_rows
        - summary.dropped_previous_ids
        - summary.dropped_previous_text
    )


def _after_duplicate_ids(summary: CleanupSummary) -> int:
    return _after_previous_text(summary) - summary.dropped_duplicate_ids


def _parquet_table_markdown(result: FilterRunResult) -> str:
    return "\n".join(
        [
            "| File | Path | SHA-256 |",
            "| ---- | ---- | ------- |",
            f"| Local parquet | `{result.local_path}` | `{result.dataset_sha256}` |",
            f"| S3 parquet | `{result.s3_uri}` | `{result.dataset_sha256}` |",
        ]
    )


def _stance_table_markdown(counts: dict[str, dict[str, int]]) -> str:
    lines = [
        "| political_stance | low | medium | high | total |",
        "| ---------------- | --: | -----: | ---: | ----: |",
    ]
    grand = {tier: 0 for tier in CANDIDATE_TOXICITY_COLUMNS}
    for stance in CANDIDATE_STANCE_ROWS:
        cells = _tier_cells(counts.get(stance, {}))
        _add_tier_counts(grand, cells)
        lines.append(_labeled_tier_row(stance, cells))
    lines.append(_labeled_tier_row(TOTAL_LABEL, _tier_cells(grand)))
    return "\n".join(lines)


def _tier_cells(counts: dict[str, int]) -> list[int]:
    return [int(counts.get(tier, 0)) for tier in CANDIDATE_TOXICITY_COLUMNS]


def _add_tier_counts(totals: dict[str, int], cells: list[int]) -> None:
    for tier, value in zip(CANDIDATE_TOXICITY_COLUMNS, cells, strict=True):
        totals[tier] += value


def _labeled_tier_row(label: str, cells: list[int]) -> str:
    total = sum(cells)
    return f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} | {total} |"


def _right_high_sentence(result: FilterRunResult) -> str:
    return (
        "Operators kept every cleaned post in the cell for right stance and "
        f"high toxicity, because the cell had {result.right_high_available} posts. "
        f"{result.right_high_available} is fewer than {TARGET_PER_CELL}."
    )


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
