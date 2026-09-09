"""Sample 2,000 unused medium toxicity posts from leftover cleaned cells.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/upsample_medium_toxicity_posts_2026_09_08/run.py
"""

from __future__ import annotations

import sys

from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.cleanup_raw_candidate_dataset import (
    cleanup_raw_candidate_dataset,
)
from experiments.filter_posts_used_for_stimulus_dataset_2026_09_08.load_raw_candidate_dataset import (
    load_raw_candidate_dataset,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.sample_leftover_medium import (
    sample_leftover_medium,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.sources import (
    pinned_combined_source,
    pinned_sample_source,
)
from experiments.upsample_medium_toxicity_posts_2026_09_08.write import (
    print_run_summary,
    write_upsampled_dataset,
)


def main() -> int:
    """Load, clean, sample leftover medium, write, and print."""
    combined_source = pinned_combined_source()
    sample_source = pinned_sample_source()
    candidate = load_raw_candidate_dataset(combined_source)
    cleaned, _summary = cleanup_raw_candidate_dataset(candidate)
    sample = load_raw_candidate_dataset(sample_source)
    sampled, leftover_left_medium, leftover_right_medium = sample_leftover_medium(
        cleaned, sample
    )
    result = write_upsampled_dataset(
        sampled, leftover_left_medium, leftover_right_medium
    )
    print_run_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
