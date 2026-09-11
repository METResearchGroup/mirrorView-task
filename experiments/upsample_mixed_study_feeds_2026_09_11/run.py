"""Clone 1000 mixed feeds and write study_user_assignments_overprovisioned.csv.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_mixed_study_feeds_2026_09_11/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.load_study_assignments_2026_09_09.catalog import (
    build_assigned_catalog,
    load_new_catalog_rows,
    load_old_catalog_rows,
    stance_by_id,
)
from experiments.load_study_assignments_2026_09_09.constants import AssignmentRow
from experiments.load_study_assignments_2026_09_09.load import load_source_assignments
from experiments.load_study_assignments_2026_09_09.split import (
    FeedKind,
    count_kind,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.constants import (
    BASE_USER_COUNT,
    CACHE_DIRNAME,
    CLONE_COUNT,
    DEMOCRAT_LEFTOVER_LEFT_COUNT,
    DEMOCRAT_MIXED_COUNT,
    DEMOCRAT_ROW_COUNT,
    EXPERIMENTAL_S3_BUCKET,
    EXTRA_FIRST_USER_ID,
    MIXED_SOURCE_COUNT,
    OVERPROVISIONED_FILENAME,
    REPUBLICAN_LEFTOVER_LEFT_COUNT,
    REPUBLICAN_MIXED_COUNT,
    REPUBLICAN_ROW_COUNT,
    SAMPLE_SEED,
    TOTAL_USER_COUNT,
    UpsampleRunResult,
    experiment_dir,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.split_batch import (
    require_original_party_prefix,
    split_rewritten,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.upsample import (
    clone_mixed_feeds,
    concat_source_rows,
    sample_mixed_feeds,
    select_mixed_rows,
)
from experiments.upsample_mixed_study_feeds_2026_09_11.write import (
    print_run_summary,
    upload_overprovisioned_csv,
    write_overprovisioned_batch,
    write_results_md,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp


def main() -> int:
    """Load, clone mixed feeds, write the overprovisioned CSV, and print counts."""
    result = _run_pipeline()
    print_run_summary(result)
    write_results_md(result, experiment_dir(REPO_ROOT))
    return 0


def _run_pipeline() -> UpsampleRunResult:
    """Load, select mixed, sample, clone, concat, split, write, upload."""
    output_dir = experiment_dir(REPO_ROOT)
    store = CampaignObjectStore(EXPERIMENTAL_S3_BUCKET)
    source_rows, catalog = _load_source_and_catalog(store, output_dir)
    combined = _clone_and_concat(source_rows, catalog)
    democrat, republican = _split_and_check(source_rows, combined, catalog)
    result = write_overprovisioned_batch(
        combined, democrat, republican, catalog, output_dir
    )
    upload_overprovisioned_csv(
        store, (output_dir / OVERPROVISIONED_FILENAME).read_bytes()
    )
    return result


def _load_source_and_catalog(
    store: CampaignObjectStore, experiment_path: Path
) -> tuple[list[AssignmentRow], pd.DataFrame]:
    cache_dir = experiment_path / CACHE_DIRNAME
    source_rows = load_source_assignments(store, cache_dir)
    catalog = build_assigned_catalog(
        load_old_catalog_rows(),
        load_new_catalog_rows(store, cache_dir),
        source_rows,
    )
    return source_rows, catalog


def _clone_and_concat(
    source_rows: list[AssignmentRow], catalog: pd.DataFrame
) -> list[AssignmentRow]:
    mixed = select_mixed_rows(source_rows, stance_by_id(catalog))
    _require_count(len(mixed), MIXED_SOURCE_COUNT, "mixed_source")
    sampled = sample_mixed_feeds(mixed, CLONE_COUNT, SAMPLE_SEED)
    extras = clone_mixed_feeds(
        sampled, EXTRA_FIRST_USER_ID, get_current_timestamp()
    )
    combined = concat_source_rows(source_rows, extras)
    _require_count(len(combined), TOTAL_USER_COUNT, "user_count")
    _require_count(len(source_rows), BASE_USER_COUNT, "base_users")
    return combined


def _split_and_check(
    source_rows: list[AssignmentRow],
    combined: list[AssignmentRow],
    catalog: pd.DataFrame,
) -> tuple[list[AssignmentRow], list[AssignmentRow]]:
    original_democrat, original_republican = split_rewritten(source_rows)
    democrat, republican = split_rewritten(combined)
    require_original_party_prefix(
        democrat, republican, original_democrat, original_republican
    )
    _require_party_totals(democrat, republican)
    _require_kind_counts(democrat, republican, stance_by_id(catalog))
    return democrat, republican


def _require_party_totals(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> None:
    _require_count(len(democrat), DEMOCRAT_ROW_COUNT, "democrat_rows")
    _require_count(len(republican), REPUBLICAN_ROW_COUNT, "republican_rows")


def _require_kind_counts(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    stance: dict[str, str],
) -> None:
    _require_count(
        count_kind(democrat, stance, FeedKind.LEFT_ONLY),
        DEMOCRAT_LEFTOVER_LEFT_COUNT,
        "democrat_left_only",
    )
    _require_count(
        count_kind(republican, stance, FeedKind.LEFT_ONLY),
        REPUBLICAN_LEFTOVER_LEFT_COUNT,
        "republican_left_only",
    )
    _require_count(
        count_kind(democrat, stance, FeedKind.TEN_TEN),
        DEMOCRAT_MIXED_COUNT,
        "democrat_ten_ten",
    )
    _require_count(
        count_kind(republican, stance, FeedKind.TEN_TEN),
        REPUBLICAN_MIXED_COUNT,
        "republican_ten_ten",
    )


def _require_count(actual: int, expected: int, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}={actual} expected={expected}")


if __name__ == "__main__":
    sys.exit(main())
