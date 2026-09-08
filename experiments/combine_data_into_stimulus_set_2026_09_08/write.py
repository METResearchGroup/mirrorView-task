"""Write the combined parquet locally, upload it to S3, and write RESULTS.md."""

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
from experiments.combine_data_into_stimulus_set_2026_09_08.sources import (
    COMBINED_ROW_COUNT,
    CombineRunResult,
    DATASET_FILENAME,
    INTEGRATION_CROSSTAB_ORDER,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    PINNED_SOURCES,
    RESULTS_FILENAME,
    STANCE_CROSSTAB_ROWS,
    TOXICITY_CROSSTAB_COLUMNS,
)
from lib.constants import REPO_ROOT

EXPERIMENT_DIR = (
    REPO_ROOT / "experiments" / "combine_data_into_stimulus_set_2026_09_08"
)
JSON_INDENT = 2
TOTAL_LABEL = "total"
RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/combine_data_into_stimulus_set_2026_09_08/run.py"""


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
    resolved_dir = experiment_dir if experiment_dir is not None else EXPERIMENT_DIR
    resolved_store = store if store is not None else _default_store()
    local_path, body = write_local_parquet(combined, resolved_dir)
    digest = upload_dataset(body, resolved_store)
    result = _combine_run_result(
        combined, local_path, digest, overall_crosstab, integration_crosstab
    )
    write_results_md(result, resolved_dir)
    return result


def print_run_summary(result: CombineRunResult) -> None:
    """Print combined row count, URIs, SHA-256, and both crosstab tables."""
    print(f"combined_rows={result.combined_rows}")
    print(f"local_path={result.local_path}")
    print(f"s3_uri={result.s3_uri}")
    print(f"dataset_sha256={result.dataset_sha256}")
    print("overall_crosstab=")
    print(json.dumps(result.overall_crosstab, indent=JSON_INDENT))
    print("integration_crosstab=")
    print(json.dumps(result.integration_crosstab, indent=JSON_INDENT))


def write_results_md(result: CombineRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with source pins, URIs, and both crosstab tables."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def _combine_run_result(
    combined: pd.DataFrame,
    local_path: Path,
    digest: str,
    overall_crosstab: dict[str, dict[str, int]],
    integration_crosstab: dict[str, dict[str, dict[str, int]]],
) -> CombineRunResult:
    return CombineRunResult(
        combined_rows=len(combined),
        local_path=str(local_path),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        dataset_sha256=digest,
        overall_crosstab=overall_crosstab,
        integration_crosstab=integration_crosstab,
    )


def _results_markdown(result: CombineRunResult) -> str:
    return "\n".join(
        [
            *_results_preamble(result),
            "## Overall political stance by LLM toxicity tier",
            "",
            _stance_table_markdown(result.overall_crosstab),
            "",
            "## Political stance by LLM toxicity tier, by platform",
            "",
            _integration_table_markdown(result.integration_crosstab),
            "",
        ]
    )


def _results_preamble(result: CombineRunResult) -> list[str]:
    return [
        "# Combine curated data into a stimulus set, results",
        "",
        "## Command",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## Sources",
        "",
        _sources_table_markdown(),
        "",
        (
            f"Combined row count is {result.combined_rows}. "
            f"Expected row count is {COMBINED_ROW_COUNT}."
        ),
        "",
        "## Combined parquet",
        "",
        _parquet_table_markdown(result),
        "",
    ]


def _sources_table_markdown() -> str:
    lines = [
        "| Platform | Dataset id | Curated run | Object | SHA-256 | Rows |",
        "| -------- | ---------- | ----------- | ------ | ------- | ---: |",
    ]
    for source in PINNED_SOURCES:
        lines.append(
            f"| {source.integration.value} | `{source.dataset_id}` | "
            f"`{source.curated_run}` | `{source.s3_uri}` | `{source.sha256}` | "
            f"{source.expected_row_count} |"
        )
    return "\n".join(lines)


def _parquet_table_markdown(result: CombineRunResult) -> str:
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
    grand = {tier: 0 for tier in TOXICITY_CROSSTAB_COLUMNS}
    for stance in STANCE_CROSSTAB_ROWS:
        cells = _tier_cells(counts.get(stance, {}))
        _add_tier_counts(grand, cells)
        lines.append(_labeled_tier_row(stance, cells))
    lines.append(_labeled_tier_row(TOTAL_LABEL, _tier_cells(grand)))
    return "\n".join(lines)


def _integration_table_markdown(
    counts: dict[str, dict[str, dict[str, int]]],
) -> str:
    lines = [
        "| integration | political_stance | low | medium | high | total |",
        "| ----------- | ---------------- | --: | -----: | ---: | ----: |",
    ]
    grand = {tier: 0 for tier in TOXICITY_CROSSTAB_COLUMNS}
    for integration in INTEGRATION_CROSSTAB_ORDER:
        platform_counts = counts.get(integration, {})
        platform_total = {tier: 0 for tier in TOXICITY_CROSSTAB_COLUMNS}
        lines.extend(_platform_stance_rows(integration, platform_counts, platform_total))
        lines.append(_integration_row(integration, TOTAL_LABEL, _tier_cells(platform_total)))
        _add_tier_counts(grand, _tier_cells(platform_total))
    lines.append(_integration_row(TOTAL_LABEL, TOTAL_LABEL, _tier_cells(grand)))
    return "\n".join(lines)


def _platform_stance_rows(
    integration: str,
    platform_counts: dict[str, dict[str, int]],
    platform_total: dict[str, int],
) -> list[str]:
    rows: list[str] = []
    for stance in STANCE_CROSSTAB_ROWS:
        cells = _tier_cells(platform_counts.get(stance, {}))
        _add_tier_counts(platform_total, cells)
        rows.append(_integration_row(integration, stance, cells))
    return rows


def _tier_cells(counts: dict[str, int]) -> list[int]:
    return [int(counts.get(tier, 0)) for tier in TOXICITY_CROSSTAB_COLUMNS]


def _add_tier_counts(totals: dict[str, int], cells: list[int]) -> None:
    for tier, value in zip(TOXICITY_CROSSTAB_COLUMNS, cells, strict=True):
        totals[tier] += value


def _labeled_tier_row(label: str, cells: list[int]) -> str:
    total = sum(cells)
    return f"| {label} | {cells[0]} | {cells[1]} | {cells[2]} | {total} |"


def _integration_row(integration: str, stance: str, cells: list[int]) -> str:
    total = sum(cells)
    return (
        f"| {integration} | {stance} | {cells[0]} | {cells[1]} | {cells[2]} | {total} |"
    )


def _parquet_bytes(frame: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    frame.to_parquet(buffer, index=False)
    return buffer.getvalue()


def _default_store() -> CampaignObjectStore:
    return CampaignObjectStore(OUTPUT_S3_BUCKET)
