"""Generate 20-post study feeds from remaining labels.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/generate_study_user_assignments_2026_09_08/run.py \
      --remaining-labels s3://mirrorview-experimental-artifacts/experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/required_label_count_per_stimulus_post.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.generate_study_user_assignments_2026_09_08.assign import assign_feeds
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


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    raise NotImplementedError


def main(argv: list[str] | None = None) -> int:
    """Load remaining labels, assign feeds, write the CSV, and upload it."""
    args = parse_args(argv)
    experiment_dir = Path("experiments/generate_study_user_assignments_2026_09_08")
    store = CampaignObjectStore("mirrorview-experimental-artifacts")
    remaining = load_remaining_labels(
        args.remaining_labels, store, experiment_dir / "cache"
    )
    old_catalog = load_old_catalog_with_cells()
    new_catalog = load_new_catalog_with_cells(None, store, experiment_dir / "cache")
    joined = join_remaining_to_catalogs(remaining, old_catalog, new_catalog)
    write_shuffled_stimuli(joined, experiment_dir)
    assignments = assign_feeds(joined)
    local = write_assignment_csv(assignments, experiment_dir)
    digest = upload_csv(local.body, store)
    result = write_results_md(digest, experiment_dir)
    print_run_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
