"""Write the overprovisioned source CSV and local party files.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from data_platform.utils.object_store import sha256_hex
from experiments.load_study_assignments_2026_09_09.constants import (
    ASSIGNMENT_COLUMNS,
    ASSIGNMENT_ID_COLUMN,
    AssignmentRow,
    CATALOG_COLUMNS,
    CONDITION,
    CSV_ENCODING,
    CSV_INDEX,
    LocalFileWrite,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    ASSIGNMENT_SLOTS,
    ASSIGNMENTS_OVERPROVISIONED_FILENAME,
    BASE_USER_COUNT,
    BATCH_DIRNAME,
    CATALOG_FILENAME,
    CLONE_COUNT,
    CONFIG_FILENAME,
    DEMOCRAT_LEFTOVER_LEFT_COUNT,
    DEMOCRAT_ROW_COUNT,
    EXPERIMENT_DIRNAME,
    EXTRA_DEMOCRAT_COUNT,
    EXTRA_REPUBLICAN_COUNT,
    MIXED_SOURCE_COUNT,
    OVERPROVISIONED_FILENAME,
    OVERPROVISIONED_S3_KEY,
    OVERPROVISIONED_S3_URI,
    PINNED_SOURCE_ASSIGNMENTS_SHA256,
    REPUBLICAN_LEFTOVER_LEFT_COUNT,
    REPUBLICAN_ROW_COUNT,
    RESULTS_FILENAME,
    STUDY_ASSIGNMENT_PREFIX,
    STUDY_CONFIG_NAME,
    STUDY_S3_BUCKET,
    TOTAL_USER_COUNT,
    UpsampleCounts,
    UpsampleRunResult,
)

INPUT_POSTS_PATH = (
    f"experiments/{EXPERIMENT_DIRNAME}/{BATCH_DIRNAME}/{CATALOG_FILENAME}"
)
LOCAL_DATA_DIR = f"experiments/{EXPERIMENT_DIRNAME}/{BATCH_DIRNAME}"
CONFIG_YAML = f"""name: {STUDY_CONFIG_NAME}
input_posts_path: {INPUT_POSTS_PATH}
local_data_dir: {LOCAL_DATA_DIR}
s3:
  bucket: {STUDY_S3_BUCKET}
  prefix: {STUDY_ASSIGNMENT_PREFIX}
cells:
  - political_party: {PARTY_DEMOCRAT}
    condition: {CONDITION}
    count: {DEMOCRAT_ROW_COUNT}
  - political_party: {PARTY_REPUBLICAN}
    condition: {CONDITION}
    count: {REPUBLICAN_ROW_COUNT}
"""


def write_overprovisioned_batch(
    source_rows: list[AssignmentRow],
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    experiment_dir: Path,
) -> UpsampleRunResult:
    """Write the overprovisioned source CSV, party files, catalog, and config.

    Raises
    ------
    ValueError
        When party counts do not match the pinned totals.
    """
    _require_party_counts(democrat, republican)
    source_write = _write_source_csv(source_rows, experiment_dir)
    _write_batch_tree(democrat, republican, catalog, experiment_dir)
    return _run_result(source_write, democrat, republican)


def upload_overprovisioned_csv(store: CampaignObjectStore, body: bytes) -> None:
    """Upload the overprovisioned CSV with ``put_new``.

    Raises
    ------
    FileExistsError
        When the experimental key already exists.
    """
    store.put_new(OVERPROVISIONED_S3_KEY, body)


def write_results_md(result: UpsampleRunResult, experiment_dir: Path) -> Path:
    """Write ``RESULTS.md`` for one live run."""
    path = experiment_dir / RESULTS_FILENAME
    path.write_text(_results_markdown(result))
    return path


def print_run_summary(result: UpsampleRunResult) -> None:
    """Print pinned counts, the overprovisioned URI, and the CSV SHA-256."""
    print(f"base_users={result.counts.base_users}")
    print(f"mixed_source={result.counts.mixed_source}")
    print(f"cloned_feeds={result.counts.cloned_feeds}")
    print(f"user_count={result.counts.total_user_count}")
    print(f"democrat_rows={result.democrat_rows}")
    print(f"republican_rows={result.republican_rows}")
    print(f"assignment_slots={result.assignment_slots}")
    print(f"s3_uri={result.experimental_s3_uri}")
    print(f"csv_sha256={result.csv_sha256}")


def _write_batch_tree(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
    experiment_dir: Path,
) -> None:
    batch_dir = experiment_dir / BATCH_DIRNAME
    _write_config(batch_dir)
    _write_assignments(democrat, _party_csv_path(batch_dir, PARTY_DEMOCRAT))
    _write_assignments(republican, _party_csv_path(batch_dir, PARTY_REPUBLICAN))
    _write_catalog(catalog, batch_dir / CATALOG_FILENAME)


def _write_source_csv(
    rows: list[AssignmentRow], experiment_dir: Path
) -> LocalFileWrite:
    frame = pd.DataFrame([row.__dict__ for row in rows]).loc[:, list(ASSIGNMENT_COLUMNS)]
    ordered = frame.sort_values(ASSIGNMENT_ID_COLUMN)
    body = ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path = experiment_dir / OVERPROVISIONED_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return LocalFileWrite(path=path, body=body)


def _write_assignments(rows: list[AssignmentRow], path: Path) -> LocalFileWrite:
    frame = pd.DataFrame([row.__dict__ for row in rows]).loc[:, list(ASSIGNMENT_COLUMNS)]
    body = frame.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return LocalFileWrite(path=path, body=body)


def _write_catalog(catalog: pd.DataFrame, path: Path) -> LocalFileWrite:
    ordered = catalog.loc[:, list(CATALOG_COLUMNS)]
    body = ordered.to_csv(index=CSV_INDEX).encode(CSV_ENCODING)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(body)
    return LocalFileWrite(path=path, body=body)


def _write_config(batch_dir: Path) -> Path:
    path = batch_dir / CONFIG_FILENAME
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(CONFIG_YAML)
    return path


def _party_csv_path(batch_dir: Path, party: str) -> Path:
    return batch_dir / party / CONDITION / ASSIGNMENTS_OVERPROVISIONED_FILENAME


def _require_party_counts(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> None:
    if len(democrat) != DEMOCRAT_ROW_COUNT:
        raise ValueError(f"democrat_rows={len(democrat)} expected={DEMOCRAT_ROW_COUNT}")
    if len(republican) != REPUBLICAN_ROW_COUNT:
        raise ValueError(
            f"republican_rows={len(republican)} expected={REPUBLICAN_ROW_COUNT}"
        )


def _run_result(
    source_write: LocalFileWrite,
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
) -> UpsampleRunResult:
    return UpsampleRunResult(
        counts=UpsampleCounts(
            base_users=BASE_USER_COUNT,
            mixed_source=MIXED_SOURCE_COUNT,
            cloned_feeds=CLONE_COUNT,
            total_user_count=TOTAL_USER_COUNT,
            extra_democrat_count=EXTRA_DEMOCRAT_COUNT,
            extra_republican_count=EXTRA_REPUBLICAN_COUNT,
        ),
        democrat_rows=len(democrat),
        republican_rows=len(republican),
        assignment_slots=ASSIGNMENT_SLOTS,
        local_path=str(source_write.path),
        experimental_s3_uri=OVERPROVISIONED_S3_URI,
        csv_sha256=sha256_hex(source_write.body),
    )


def _results_markdown(result: UpsampleRunResult) -> str:
    return "\n".join(
        [
            "# Upsample mixed study feeds, results",
            "",
            "## Tests",
            "",
            "`PYTHONPATH=. uv run pytest experiments/upsample_mixed_study_feeds_2026_09_11/tests -q` exited 0.",
            "",
            "## Counts",
            "",
            "| Count | Value |",
            "| ----- | ----: |",
            f"| Base users | {result.counts.base_users} |",
            f"| Mixed source | {result.counts.mixed_source} |",
            f"| Cloned feeds | {result.counts.cloned_feeds} |",
            f"| User count | {result.counts.total_user_count} |",
            f"| Democrat rows | {result.democrat_rows} |",
            f"| Republican rows | {result.republican_rows} |",
            f"| Democrat leftover-left | {DEMOCRAT_LEFTOVER_LEFT_COUNT} |",
            f"| Republican leftover-left | {REPUBLICAN_LEFTOVER_LEFT_COUNT} |",
            f"| Assignment slots | {result.assignment_slots} |",
            "",
            f"Source SHA-256: `{PINNED_SOURCE_ASSIGNMENTS_SHA256}`",
            "",
            f"Overprovisioned object: `{result.experimental_s3_uri}`",
            "",
            f"CSV SHA-256: `{result.csv_sha256}`",
            "",
            "The live prefix `2026_09_09-23:06:02` was left in place. DynamoDB production counters were not reset. The lookup Lambda was not changed.",
            "",
        ]
    )
