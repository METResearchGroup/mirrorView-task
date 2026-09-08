"""Count remaining labels per stimulus post for the old catalog and the new sample.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned new sample parquet exists at SHA-256 9788331f898aa27352dcdf32a962b5722aecc1da61a4638b7bbd77a404415ab9
when PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
then old_posts=8899
and old_labels=27557
and new_posts=10200
and new_labels=51000
and total_posts=19099
and total_labels=78557
and local required_label_count_per_stimulus_post.csv exists
and S3 object experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/required_label_count_per_stimulus_post.csv exists
and its SHA-256 matches the local file
and every number_of_times_to_label value is greater than 0
and RESULTS.md contains total remaining labels 78557
and RESULTS.md contains old remaining labels 27557
and RESULTS.md contains new remaining labels 51000
and stdout prints those counts

given the S3 CSV key already exists
when the command is run again
then the process raises FileExistsError and does not change the new sample parquet

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import sys

from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.calculate import (
    calculate_required_label_counts,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.constants import (
    pinned_new_sample,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.load import (
    load_new_sample,
    load_old_catalog,
    load_old_results,
)
from experiments.calculate_required_label_count_per_stimulus_post_2026_09_08.write import (
    print_run_summary,
    write_required_label_counts,
)


def main() -> int:
    """Load both batches, compute remaining labels, write, and print."""
    source = pinned_new_sample()
    old_catalog = load_old_catalog()
    old_results = load_old_results()
    new_sample = load_new_sample(source, _store(), _cache_dir())
    counts = calculate_required_label_counts(
        old_catalog, old_results, new_sample, _required_labels_per_post()
    )
    result = write_required_label_counts(
        counts, source, _experiment_dir(), _store(), _old_catalog_id_count(old_catalog)
    )
    print_run_summary(result)
    return 0


def _store():
    raise NotImplementedError


def _cache_dir():
    raise NotImplementedError


def _experiment_dir():
    raise NotImplementedError


def _required_labels_per_post() -> int:
    raise NotImplementedError


def _old_catalog_id_count(old_catalog) -> int:
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
