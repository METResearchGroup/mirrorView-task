"""Count remaining labels per stimulus post for the old catalog and the new sample.

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
    old_catalog = load_old_catalog()
    old_results = load_old_results()
    new_sample = load_new_sample(pinned_new_sample())
    counts = calculate_required_label_counts(old_catalog, old_results, new_sample)
    result = write_required_label_counts(counts)
    print_run_summary(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
