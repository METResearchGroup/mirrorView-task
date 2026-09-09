"""Generate 20-post study feeds from remaining labels.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from data_platform.generate_features.s3_feature_campaign import (
    CampaignObjectStore,
    s3_uri,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    pinned_new_catalog,
)
from experiments.generate_study_user_assignments_2026_09_08.assign import (
    assign_feeds,
    count_feed_kinds,
)
from experiments.generate_study_user_assignments_2026_09_08.constants import (
    AssignmentRunResult,
    CACHE_DIRNAME,
    CELL_COLUMN,
    CELL_COUNT,
    EXPERIMENT_DIRNAME,
    MISSING_REMAINING_LABELS_ERROR,
    OUTPUT_S3_BUCKET,
    OUTPUT_S3_KEY,
    POST_ID_COLUMN,
    POSTS_PER_FEED,
    REMAINING_COUNT_COLUMN,
    REMAINING_LABELS_FLAG,
    STANCE_COLUMN,
    STANCE_LEFT,
    STANCE_RIGHT,
    UserAssignment,
)
from experiments.generate_study_user_assignments_2026_09_08.load import (
    join_remaining_to_catalogs,
    load_new_catalog_with_cells,
    load_old_catalog_with_cells,
    load_remaining_labels,
    write_shuffled_stimuli,
)
from experiments.generate_study_user_assignments_2026_09_08.write import (
    print_run_summary,
    upload_csv,
    write_assignment_csv,
    write_results_md,
)
from lib.constants import REPO_ROOT
from lib.timestamp_utils import get_current_timestamp


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ``--remaining-labels``. Exit non-zero when the path is omitted.

    Parameters
    ----------
    argv
        Argument list. ``None`` reads ``sys.argv``.

    Returns
    -------
    argparse.Namespace
        Namespace with ``remaining_labels``.

    Raises
    ------
    SystemExit
        When ``--remaining-labels`` is missing.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument(REMAINING_LABELS_FLAG, dest="remaining_labels", default=None)
    args = parser.parse_args(argv)
    if args.remaining_labels is None:
        print(MISSING_REMAINING_LABELS_ERROR, file=sys.stderr)
        raise SystemExit(2)
    return args


def main(argv: list[str] | None = None) -> int:
    """Load remaining labels, assign feeds, write the CSV, and upload it."""
    args = parse_args(argv)
    experiment_dir = REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    cache_dir = experiment_dir / CACHE_DIRNAME
    remaining = load_remaining_labels(args.remaining_labels, store, cache_dir)
    old_catalog = load_old_catalog_with_cells()
    new_catalog = load_new_catalog_with_cells(pinned_new_catalog(), store, cache_dir)
    joined = join_remaining_to_catalogs(remaining, old_catalog, new_catalog)
    write_shuffled_stimuli(joined, experiment_dir)
    assignments = assign_feeds(joined)
    local = write_assignment_csv(assignments, experiment_dir, get_current_timestamp())
    digest = upload_csv(local.body, store)
    result = _run_result(assignments, joined, local.path, digest)
    write_results_md(result, experiment_dir)
    print_run_summary(result)
    return 0


def _run_result(
    assignments: list[UserAssignment],
    joined: pd.DataFrame,
    local_path: Path,
    digest: str,
) -> AssignmentRunResult:
    kinds = count_feed_kinds(
        _stance_remaining(joined, STANCE_LEFT),
        _stance_remaining(joined, STANCE_RIGHT),
    )
    extras = _extra_counts(assignments, joined)
    return AssignmentRunResult(
        ten_ten_count=kinds.ten_ten_count,
        left_only_count=kinds.left_only_count,
        user_count=kinds.user_count,
        assignment_rows=len(assignments),
        assignment_slots=len(assignments) * POSTS_PER_FEED,
        extra_labels=extras.extra_labels,
        extra_left=extras.extra_left,
        extra_right=extras.extra_right,
        unused_remaining=extras.unused_remaining,
        remaining_by_cell=_by_cell_remaining(joined),
        assigned_by_cell=_by_cell_assigned(assignments, joined),
        local_path=str(local_path.relative_to(REPO_ROOT)),
        s3_uri=s3_uri(OUTPUT_S3_BUCKET, OUTPUT_S3_KEY),
        csv_sha256=digest,
    )


def _stance_remaining(joined: pd.DataFrame, stance: str) -> int:
    return int(joined.loc[joined[STANCE_COLUMN] == stance, REMAINING_COUNT_COLUMN].sum())


@dataclass(frozen=True)
class _ExtraCounts:
    extra_labels: int
    extra_left: int
    extra_right: int
    unused_remaining: int


def _extra_counts(assignments: list[UserAssignment], joined: pd.DataFrame) -> _ExtraCounts:
    assigned = Counter(
        post_id for assignment in assignments for post_id in assignment.post_ids
    )
    stance_by_id = dict(zip(joined[POST_ID_COLUMN].astype(str), joined[STANCE_COLUMN]))
    extra_left = 0
    extra_right = 0
    unused = 0
    for post_id, remaining in zip(
        joined[POST_ID_COLUMN].astype(str), joined[REMAINING_COUNT_COLUMN].astype(int)
    ):
        used = assigned[post_id]
        extra = max(0, used - remaining)
        unused += max(0, remaining - used)
        if stance_by_id[post_id] == STANCE_LEFT:
            extra_left += extra
        else:
            extra_right += extra
    return _ExtraCounts(
        extra_labels=extra_left + extra_right,
        extra_left=extra_left,
        extra_right=extra_right,
        unused_remaining=unused,
    )


def _by_cell_remaining(joined: pd.DataFrame) -> tuple[int, int, int, int, int, int]:
    counts = [
        int(joined.loc[joined[CELL_COLUMN] == cell, REMAINING_COUNT_COLUMN].sum())
        for cell in range(1, CELL_COUNT + 1)
    ]
    return tuple(counts)


def _by_cell_assigned(
    assignments: list[UserAssignment], joined: pd.DataFrame
) -> tuple[int, int, int, int, int, int]:
    cell_by_id = dict(zip(joined[POST_ID_COLUMN].astype(str), joined[CELL_COLUMN].astype(int)))
    counts = [0] * CELL_COUNT
    for assignment in assignments:
        for post_id in assignment.post_ids:
            counts[cell_by_id[post_id] - 1] += 1
    return tuple(counts)


if __name__ == "__main__":
    sys.exit(main())
