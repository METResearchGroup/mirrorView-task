"""Count remaining labels for the old catalog and the pull request 273 catalog.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and pull request 273 wrote the 10000 row catalog
when PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py
then old_posts=8899
and old_labels=27557
and new_posts=10000
and new_labels=50000
and total_posts=18899
and total_labels=77557
and every number_of_times_to_label value is greater than 0
and the S3 CSV SHA-256 matches the local file
and RESULTS.md records those totals

given the S3 CSV key already exists
when the command is run again
then the process raises FileExistsError
and the v1 remaining-label CSV is unchanged
and the v2 remaining-label CSV is unchanged

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_09/run.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from data_platform.generate_features.s3_feature_campaign import CampaignObjectStore
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.calculate import (
    calculate_required_label_counts,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.constants import (
    CACHE_DIRNAME,
    EXPERIMENT_DIRNAME,
    LabelCountRunResult,
    OUTPUT_S3_BUCKET,
    REQUIRED_LABELS_PER_POST,
    pinned_new_catalog,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.load import (
    load_new_catalog,
    load_old_catalog,
    load_old_results,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_09.write import (
    print_run_summary,
    require_output_key_absent,
    write_required_label_counts,
)
from lib.constants import REPO_ROOT


def main() -> int:
    """Count remaining labels for the old catalog and the new catalog."""
    print_run_summary(_run_pipeline())
    return 0


def _run_pipeline() -> LabelCountRunResult:
    source = pinned_new_catalog()
    experiment_dir = _experiment_dir()
    store = CampaignObjectStore(OUTPUT_S3_BUCKET)
    require_output_key_absent(store)
    old_catalog = load_old_catalog()
    old_results = load_old_results()
    new_catalog = load_new_catalog(source, store, experiment_dir / CACHE_DIRNAME)
    counts = calculate_required_label_counts(
        old_catalog, old_results, new_catalog, REQUIRED_LABELS_PER_POST
    )
    return write_required_label_counts(
        counts, source, experiment_dir, store, len(old_catalog)
    )


def _experiment_dir() -> Path:
    return REPO_ROOT / "experiments" / EXPERIMENT_DIRNAME


if __name__ == "__main__":
    sys.exit(main())
