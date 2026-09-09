"""Convert the pull request 278 assignment CSV into party files and a catalog.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/load_study_assignments_2026_09_09/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    parse_s3_uri,
)
from experiments.load_study_assignments_2026_09_09.catalog import (
    build_assigned_catalog,
    load_new_catalog_rows,
    load_old_catalog_rows,
    stance_by_id,
)
from experiments.load_study_assignments_2026_09_09.constants import (
    AssignmentRow,
    CACHE_DIRNAME,
    DEMOCRAT_LEFT_ONLY_COUNT,
    DEMOCRAT_ROW_COUNT,
    DEMOCRAT_TEN_TEN_COUNT,
    EXPERIMENT_DIRNAME,
    FeedKind,
    LoadRunResult,
    PARTY_DEMOCRAT,
    PARTY_REPUBLICAN,
    PINNED_ASSIGNMENTS_S3_URI,
    REPUBLICAN_LEFT_ONLY_COUNT,
    REPUBLICAN_ROW_COUNT,
    REPUBLICAN_TEN_TEN_COUNT,
)
from experiments.load_study_assignments_2026_09_09.load import load_source_assignments
from experiments.load_study_assignments_2026_09_09.split import (
    count_kind,
    feed_kind,
    parse_post_ids,
    rewrite_ids,
    split_by_party,
)
from experiments.load_study_assignments_2026_09_09.write import (
    print_run_summary,
    write_batch,
)
from lib.constants import REPO_ROOT


def main() -> int:
    """Convert the pinned assignment CSV and write the local batch tree."""
    print_run_summary(_run_pipeline())
    return 0


def _run_pipeline() -> LoadRunResult:
    experiment_dir = _experiment_dir()
    bucket, _key = parse_s3_uri(PINNED_ASSIGNMENTS_S3_URI)
    store = CampaignObjectStore(bucket)
    return _convert_and_write(store, experiment_dir)


def _convert_and_write(
    store: CampaignObjectStore, experiment_dir: Path
) -> LoadRunResult:
    source_rows = load_source_assignments(store, experiment_dir / CACHE_DIRNAME)
    democrat, republican = _split_and_rewrite(source_rows)
    catalog = _assigned_catalog(store, experiment_dir / CACHE_DIRNAME, democrat + republican)
    _require_counts(democrat, republican, catalog)
    return write_batch(democrat, republican, catalog, experiment_dir)


def _split_and_rewrite(
    source_rows: list[AssignmentRow],
) -> tuple[list[AssignmentRow], list[AssignmentRow]]:
    democrat, republican = split_by_party(source_rows)
    return rewrite_ids(democrat, PARTY_DEMOCRAT), rewrite_ids(
        republican, PARTY_REPUBLICAN
    )


def _assigned_catalog(
    store: CampaignObjectStore,
    cache_dir: Path,
    rows: list[AssignmentRow],
) -> pd.DataFrame:
    return build_assigned_catalog(
        load_old_catalog_rows(),
        load_new_catalog_rows(store, cache_dir),
        rows,
    )


def _require_counts(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    catalog: pd.DataFrame,
) -> None:
    _require_party_counts(democrat, republican)
    stance_lookup = stance_by_id(catalog)
    _require_known_feed_kinds(democrat + republican, stance_lookup)
    _require_left_only_counts(democrat, republican, stance_lookup)


def _require_party_counts(
    democrat: list[AssignmentRow], republican: list[AssignmentRow]
) -> None:
    if len(democrat) != DEMOCRAT_ROW_COUNT:
        raise ValueError(f"democrat_rows={len(democrat)} expected={DEMOCRAT_ROW_COUNT}")
    if len(republican) != REPUBLICAN_ROW_COUNT:
        raise ValueError(
            f"republican_rows={len(republican)} expected={REPUBLICAN_ROW_COUNT}"
        )


def _require_known_feed_kinds(
    rows: list[AssignmentRow], stance_lookup: dict[str, str]
) -> None:
    for row in rows:
        feed_kind(parse_post_ids(row.assigned_post_ids), stance_lookup)


def _require_left_only_counts(
    democrat: list[AssignmentRow],
    republican: list[AssignmentRow],
    stance_lookup: dict[str, str],
) -> None:
    _require_kind_count(democrat, stance_lookup, FeedKind.LEFT_ONLY, DEMOCRAT_LEFT_ONLY_COUNT)
    _require_kind_count(
        republican, stance_lookup, FeedKind.LEFT_ONLY, REPUBLICAN_LEFT_ONLY_COUNT
    )
    _require_kind_count(democrat, stance_lookup, FeedKind.TEN_TEN, DEMOCRAT_TEN_TEN_COUNT)
    _require_kind_count(
        republican, stance_lookup, FeedKind.TEN_TEN, REPUBLICAN_TEN_TEN_COUNT
    )


def _require_kind_count(
    rows: list[AssignmentRow],
    stance_lookup: dict[str, str],
    kind: FeedKind,
    expected: int,
) -> None:
    actual = count_kind(rows, stance_lookup, kind)
    if actual != expected:
        raise ValueError(f"{kind.value}={actual} expected={expected}")


def _experiment_dir() -> Path:
    return REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME


if __name__ == "__main__":
    sys.exit(main())
