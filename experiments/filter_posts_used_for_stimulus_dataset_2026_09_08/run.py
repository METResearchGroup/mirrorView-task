"""Filter the combined stimulus parquet to a balanced sample.

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
