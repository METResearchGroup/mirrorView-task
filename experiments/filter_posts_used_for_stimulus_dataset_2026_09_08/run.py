"""Filter the combined stimulus parquet to a balanced sample.

given AWS credentials from LAB_AWS_ACCESS_KEY_ID and LAB_AWS_ACCESS_KEY_SECRET
and the pinned combined parquet exists at SHA-256 f24ad1fd8c3709ffbbba9fb5dc953dcaee2f11ad8916ae21612b7f25cb5ca3f0
when PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
then candidate_rows=55573
and cleaned_rows=54472
and sampled_rows=9562
and local dataset.parquet exists
and S3 object experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/dataset.parquet exists
and its SHA-256 matches the local file
and RESULTS.md contains the cleaned stance by toxicity table
and RESULTS.md contains the sampled stance by toxicity table
and the sampled right-high cell has 1062 rows
and stdout prints both tables

given the S3 dataset.parquet key already exists
when the command is run again
then the process raises FileExistsError and does not change the combined source object

Run from the repo root:

    PYTHONPATH=. uv run python experiments/filter_posts_used_for_stimulus_dataset_2026_09_08/run.py
"""

from __future__ import annotations

import sys

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.cleanup_raw_candidate_dataset import (
    cleanup_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.load_raw_candidate_dataset import (
    load_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sample_raw_candidate_dataset import (
    sample_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.sources import (
    pinned_candidate_source,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.upload_filtered_candidate_dataset import (
    print_run_summary,
    write_filtered_dataset,
)


def main() -> int:
    """Load, clean, sample, write, and print the filtered stimulus dataset."""
    source = pinned_candidate_source()
    candidate = load_raw_candidate_dataset(source)
    cleaned, summary = cleanup_raw_candidate_dataset(candidate)
    sampled = sample_raw_candidate_dataset(cleaned)
    result = write_filtered_dataset(sampled, cleaned, summary)
    print_run_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
