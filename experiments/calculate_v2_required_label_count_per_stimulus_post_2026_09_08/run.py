"""Count remaining labels for the old catalog and the new 10,000 row catalog.

Run from the repo root:

    PYTHONPATH=. uv run python experiments/calculate_v2_required_label_count_per_stimulus_post_2026_09_08/run.py
"""

from __future__ import annotations

import sys

from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.calculate import (
    calculate_required_label_counts,
)
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.constants import (
    REQUIRED_LABELS_PER_POST,
    pinned_new_catalog,
)
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.load import (
    load_new_catalog,
    load_old_catalog,
    load_old_results,
)
from experiments.calculate_v2_required_label_count_per_stimulus_post_2026_09_08.write import (
    print_run_summary,
    write_required_label_counts,
)


def main() -> int:
    """Load both batches, compute remaining labels, write, and print."""
    raise NotImplementedError


if __name__ == "__main__":
    sys.exit(main())
