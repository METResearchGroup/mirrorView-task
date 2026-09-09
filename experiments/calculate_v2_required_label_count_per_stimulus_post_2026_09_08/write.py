"""Write remaining label counts locally, upload to S3, and write RESULTS.md."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from data_platform.utils.object_store import sha256_hex
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.constants import (
    Batch,
    CSV_INDEX,
    DATASET_FILENAME,
    LabelCountRunResult,
    LocalCsvWrite,
    NewCatalogSource,
    OUTPUT_BATCH_COLUMN,
    OUTPUT_COLUMNS,
    OUTPUT_COUNT_COLUMN,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    REQUIRED_LABELS_PER_POST,
    RESULTS_FILENAME,
)
from lib.constants import REPO_ROOT

CSV_ENCODING = "utf-8"
OLD_CATALOG_DISPLAY_PATH = "shared/data/raw/study_phase_2_part_2/stimuli/flips.csv"
RUN_COMMAND = """export AWS_ACCESS_KEY_ID="$LAB_AWS_ACCESS_KEY_ID"
export AWS_SECRET_ACCESS_KEY="$LAB_AWS_ACCESS_KEY_SECRET"

PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py"""


def write_local_csv(counts: pd.DataFrame, experiment_dir: Path) -> LocalCsvWrite:
    """Write the remaining-label CSV under the experiment folder."""
    body = _csv_bytes(counts)
    path = experiment_dir / DATASET_FILENAME
    path.write_bytes(body)
    return LocalCsvWrite(path=path, body=body)


def upload_csv(body: bytes, store: CampaignObjectStore) -> str:
    """Upload CSV bytes with put_new and return the SHA-256.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    store.put_new(OUTPUT_S3_KEY, body)
    return sha256_hex(body)


def write_results_md(result: LabelCountRunResult, experiment_dir: Path) -> Path:
    """Write RESULTS.md with remaining-label totals."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def write_required_label_counts(
    counts: pd.DataFrame,
    source: NewCatalogSource,
    experiment_dir: Path,
    store: CampaignObjectStore,
    old_catalog_ids: int,
) -> LabelCountRunResult:
    """Write the local CSV, upload it once, and write RESULTS.md.

    Raises
    ------
    FileExistsError
        When the destination S3 key already exists.
    """
    local = write_local_csv(counts, experiment_dir)
    digest = upload_csv(local.body, store)
    result = _label_count_run_result(counts, source, local.path, digest, old_catalog_ids)
    write_results_md(result, experiment_dir)
    return result


def print_run_summary(result: LabelCountRunResult) -> None:
    """Print remaining label totals and the S3 URI."""
    print(f"old_posts={result.old_posts}")
    print(f"old_labels={result.old_labels}")
    print(f"new_posts={result.new_posts}")
    print(f"new_labels={result.new_labels}")
    print(f"total_posts={result.total_posts}")
    print(f"total_labels={result.total_labels}")
    print(f"s3_uri={result.s3_uri}")
    print(f"csv_sha256={result.csv_sha256}")


def _csv_bytes(counts: pd.DataFrame) -> bytes:
    ordered = counts.loc[:, list(OUTPUT_COLUMNS)]
    return ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)


def _label_count_run_result(
    counts: pd.DataFrame,
    source: NewCatalogSource,
    local_path: Path,
    digest: str,
    old_catalog_ids: int,
) -> LabelCountRunResult:
    old_posts, old_labels = _batch_totals(counts, Batch.OLD)
    new_posts, new_labels = _batch_totals(counts, Batch.NEW)
    return LabelCountRunResult(
        old_catalog_ids=old_catalog_ids,
        old_posts=old_posts,
        old_labels=old_labels,
        new_posts=new_posts,
        new_labels=new_labels,
        total_posts=len(counts),
        total_labels=int(counts[OUTPUT_COUNT_COLUMN].sum()),
        local_path=str(local_path.relative_to(REPO_ROOT)),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        csv_sha256=digest,
        new_catalog_uri=source.s3_uri,
        new_catalog_sha256=source.sha256,
        new_catalog_rows=source.expected_row_count,
    )


def _batch_totals(counts: pd.DataFrame, batch: Batch) -> tuple[int, int]:
    rows = counts[counts[OUTPUT_BATCH_COLUMN] == batch.value]
    return len(rows), int(rows[OUTPUT_COUNT_COLUMN].sum())


def _results_markdown(result: LabelCountRunResult) -> str:
    return "\n".join([*_results_preamble(result), *_results_totals(result)])


def _results_preamble(result: LabelCountRunResult) -> list[str]:
    return [
        "# Calculate v2 required label count per stimulus post, results",
        "",
        "## Command",
        "",
        "```bash",
        RUN_COMMAND,
        "```",
        "",
        "## New catalog",
        "",
        _new_catalog_sentence(result),
        "",
        "## Old catalog",
        "",
        _old_catalog_sentence(result),
        "",
    ]


def _results_totals(result: LabelCountRunResult) -> list[str]:
    return [
        "## Remaining labels",
        "",
        _csv_table_markdown(result),
        "",
        _totals_table_markdown(result),
        "",
    ]


def _new_catalog_sentence(result: LabelCountRunResult) -> str:
    return (
        f"Object `{result.new_catalog_uri}` SHA-256 `{result.new_catalog_sha256}` "
        f"has {result.new_catalog_rows} rows."
    )


def _old_catalog_sentence(result: LabelCountRunResult) -> str:
    return (
        f"Catalog `{OLD_CATALOG_DISPLAY_PATH}` has {result.old_catalog_ids} unique ids. "
        f"Remaining labels equal {REQUIRED_LABELS_PER_POST} minus the number of unique "
        "`prolific_id` raters per `post_id`."
    )


def _csv_table_markdown(result: LabelCountRunResult) -> str:
    return "\n".join(
        [
            "| File | Path | SHA-256 |",
            "| ---- | ---- | ------- |",
            f"| Local CSV | `{result.local_path}` | `{result.csv_sha256}` |",
            f"| S3 CSV | `{result.s3_uri}` | `{result.csv_sha256}` |",
        ]
    )


def _totals_table_markdown(result: LabelCountRunResult) -> str:
    return "\n".join(
        [
            "| Batch | Posts | Remaining labels |",
            "| ----- | ----: | ---------------: |",
            f"| old | {result.old_posts} | {result.old_labels} |",
            f"| new | {result.new_posts} | {result.new_labels} |",
            f"| total | {result.total_posts} | {result.total_labels} |",
        ]
    )
